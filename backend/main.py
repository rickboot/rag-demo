"""FastAPI app: health, hello, chat, and static frontend."""

from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings

from backend.agent import run_rag_chat
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
