"""FastAPI app: health, hello, chat, and static frontend."""

from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings

import uuid

from backend.agent import run_rag_chat
from backend.degradation import NUM_DEGRADATION_TURNS, run_degradation_test, run_degradation_turn
from backend.retrieval import retrieve

app = FastAPI(
    title="RAG Demo",
    description="RAG + agentic coding assistant for Phison aiDAPTIV",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health")
def health() -> dict:
    """Health check for load balancers and scripts."""
    return {"status": "ok", "tier": settings.tier}


@app.get("/api/hello")
def hello() -> dict:
    """Hello payload for frontend to display."""
    return {
        "status": "ok",
        "tier": settings.tier,
        "message": "RAG Demo backend is running.",
        "inference_url": settings.inference_url,
        "model": settings.model_name,
    }


@app.get("/api/model-info")
async def api_model_info() -> dict:
    """Model name, quant, context length, and memory (from Ollama show + ps when available)."""
    out = {
        "model": settings.model_name,
        "quant": None,
        "parameter_size": None,
        "context_length": settings.context_length,
        "size_vram_mb": None,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            show_url = f"{settings.inference_url}/api/show"
            resp = await client.post(show_url, json={"model": settings.model_name})
            if resp.status_code == 200:
                data = resp.json()
                details = data.get("details") or {}
                out["quant"] = details.get("quantization_level")
                out["parameter_size"] = details.get("parameter_size")
                model_info = data.get("model_info") or {}
                for k, v in model_info.items():
                    if "context_length" in k.lower() and isinstance(v, (int, float)):
                        out["context_length"] = int(v)
                        break
            ps_url = f"{settings.inference_url}/api/ps"
            ps_resp = await client.get(ps_url)
            if ps_resp.status_code == 200:
                ps_data = ps_resp.json()
                models = ps_data.get("models") or []
                for m in models:
                    if m.get("name", "").startswith(settings.model_name) or settings.model_name in m.get("name", ""):
                        size_vram = m.get("size_vram") or m.get("size")
                        if size_vram is not None:
                            out["size_vram_mb"] = round(size_vram / (1024 * 1024), 2)
                        break
    except Exception:
        pass
    return out


def _index_dir() -> Path:
    p = settings.index_path.expanduser().resolve()
    return p.parent if p.suffix else p


@app.get("/api/corpus")
def api_corpus() -> dict:
    """Workload/codebase info: name, file count, chunks, lines, index size. From metadata.json + index."""
    import json
    out = {
        "codebase_name": getattr(settings.repo_path, "name", None) or str(settings.repo_path),
        "num_files": 0,
        "num_chunks": 0,
        "total_chars": 0,
        "total_lines": 0,
        "index_size_mb": 0.0,
        "metadata_size_mb": 0.0,
    }
    idx_dir = _index_dir()
    meta_path = idx_dir / "metadata.json"
    index_path = idx_dir / "index.faiss"
    if not meta_path.exists():
        return out
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, list):
            return out
        out["num_chunks"] = len(metadata)
        out["num_files"] = len({m.get("path") for m in metadata if m.get("path")})
        out["total_chars"] = sum(len(m.get("text") or "") for m in metadata)
        out["total_lines"] = sum((m.get("text") or "").count("\n") for m in metadata)
        if index_path.exists():
            out["index_size_mb"] = round(index_path.stat().st_size / (1024 * 1024), 2)
        out["metadata_size_mb"] = round(meta_path.stat().st_size / (1024 * 1024), 2)
    except Exception:
        pass
    return out


# In-memory session store: session_id -> list of {role, content}
_sessions: dict[str, list[dict]] = {}


def _get_or_create_session(session_id: str | None) -> tuple[str, list[dict]]:
    import uuid
    sid = (session_id or "").strip() or str(uuid.uuid4())
    if sid not in _sessions:
        _sessions[sid] = []
    return sid, _sessions[sid]


def _session_metrics(history: list[dict]) -> dict:
    """Telemetry for Phase 6: message count, approximate context size, optional process memory."""
    message_count = len(history)
    context_chars = sum(len((m.get("content") or "")) for m in history)
    metrics: dict = {
        "message_count": message_count,
        "context_chars": context_chars,
    }
    try:
        import psutil
        proc = psutil.Process()
        metrics["process_rss_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass
    return metrics


class ChatRequest(BaseModel):
    prompt: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    message_count: int = 0
    metrics: dict = {}

    model_config = {"extra": "allow"}


class SessionResponse(BaseModel):
    session_id: str
    message_count: int
    metrics: dict = {}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """RAG coding assistant: retrieve context, then LLM. Multi-turn via session_id."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")
    session_id, history = _get_or_create_session(req.session_id)
    history.append({"role": "user", "content": req.prompt})
    try:
        reply, turn_metrics = await run_rag_chat(req.prompt, history[:-1])  # history without this turn
        history.append({"role": "assistant", "content": reply})
        metrics = _session_metrics(history)
        metrics["last_turn"] = turn_metrics
        return ChatResponse(
            reply=reply,
            session_id=session_id,
            message_count=metrics["message_count"],
            metrics=metrics,
        )
    except httpx.ConnectError as e:
        history.pop()  # remove the user message we just appended
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach inference at {settings.inference_url}. Is Ollama running?",
        ) from e
    except httpx.HTTPStatusError as e:
        history.pop()
        raise HTTPException(status_code=502, detail=str(e.response.text)) from e


@app.get("/api/session/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """Return session telemetry: message count and metrics (Phase 6)."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="session not found")
    history = _sessions[session_id]
    metrics = _session_metrics(history)
    return SessionResponse(
        session_id=session_id,
        message_count=metrics["message_count"],
        metrics=metrics,
    )


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 10


class RetrieveResponse(BaseModel):
    chunks: list[dict]


class RunDegradationTurnRequest(BaseModel):
    session_id: str | None = None
    prompt_index: int


@app.post("/run-degradation-test")
async def api_run_degradation_test() -> dict:
    """Run predefined 15-turn sequence against RAG + chat; single session, metrics per turn."""
    session_id = str(uuid.uuid4())
    try:
        result = await run_degradation_test(session_id, _sessions)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/run-degradation-test-turn")
async def api_run_degradation_test_turn(req: RunDegradationTurnRequest) -> dict:
    """Run one degradation turn; client calls this 15 times (prompt_index 0..14) to show each turn as it completes."""
    if not (0 <= req.prompt_index < NUM_DEGRADATION_TURNS):
        raise HTTPException(
            status_code=400,
            detail=f"prompt_index must be 0..{NUM_DEGRADATION_TURNS - 1}",
        )
    try:
        return await run_degradation_turn(req.session_id, req.prompt_index, _sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/retrieve", response_model=RetrieveResponse)
def api_retrieve(req: RetrieveRequest) -> RetrieveResponse:
    """Search Transformers corpus; return top-k chunks with path, text, score."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    try:
        chunks = retrieve(req.query.strip(), top_k=min(req.top_k, 50))
        return RetrieveResponse(chunks=chunks)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@app.get("/")
def index() -> FileResponse:
    """Serve frontend so one URL runs the app."""
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "frontend/index.html not found"}, status_code=404)
    return FileResponse(index_file)


# Static assets (e.g. future JS/CSS) from same dir as index.html
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
