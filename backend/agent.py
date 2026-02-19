"""
RAG agent: retrieve chunks for query, build prompt with context + history, call LLM.
Explicit agent loop (retrieve → format → complete). Session state lives in main.
"""

from backend.inference import generate
from backend.retrieval import retrieve
from config import settings

def _format_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        path = c.get("path", "?")
        text = (c.get("text") or "")[:2000].strip()
        parts.append(f"[{i}] {path}\n{text}")
    return "\n\n".join(parts)[: settings.max_context_chars]


def _format_messages(history: list[dict]) -> str:
    lines = []
    for m in history:
        role = (m.get("role") or "user").lower()
        content = (m.get("content") or "").strip()
        if role == "user":
            lines.append(f"User: {content}")
        else:
            lines.append(f"Assistant: {content}")
    return "\n".join(lines) if lines else "(no prior messages)"


async def run_rag_chat(message: str, history: list[dict]) -> tuple[str, dict]:
    """
    Run one agent step: retrieve for message, build prompt with context + history, return LLM reply.
    """
    import time

    message = (message or "").strip()
    if not message:
        return "Please ask a question about the codebase.", {"error": "empty_message"}

    try:
        t_retrieve0 = time.perf_counter()
        chunks = retrieve(message, top_k=settings.rag_top_k)
        t_retrieve1 = time.perf_counter()
    except FileNotFoundError:
        return (
            "RAG index not loaded. Run: uv run python -m ingest (or use test index).",
            {"error": "index_not_loaded"},
        )

    context = _format_context(chunks) if chunks else "(no relevant chunks found)"
    conv = _format_messages(history)

    system = (
        "You are a coding assistant with access to the Hugging Face Transformers codebase. "
        "Use the following retrieved code snippets only to ground your answer. "
        "If the snippets do not contain relevant information, say so and answer from general knowledge."
    )
    prompt = f"""{system}

## Retrieved context (file excerpts)
{context}

## Conversation so far
{conv}

## Current user message
User: {message}

## Your reply (concise, grounded in the context when possible)
Assistant:"""

    t_infer0 = time.perf_counter()
    reply, infer_meta = await generate(prompt)
    t_infer1 = time.perf_counter()

    # Compact per-turn telemetry for demo/operator visibility.
    chunk_list = chunks or []
    paths = [c.get("path") for c in chunk_list if c.get("path")]
    top = [
        {"path": c.get("path"), "score": c.get("score")}
        for c in chunk_list[: min(3, len(chunk_list))]
    ]
    turn_metrics = {
        "tier": settings.tier,
        "model": settings.model_name,
        "rag": {
            "top_k": settings.rag_top_k,
            "returned": len(chunk_list),
            "paths": paths,
            "top": top,
        },
        "sizes": {
            "prompt_chars": len(prompt),
            "context_chars": len(context),
            "history_messages": len(history),
        },
        "timing_ms": {
            "retrieve_ms": round((t_retrieve1 - t_retrieve0) * 1000.0, 2),
            "inference_ms": round((t_infer1 - t_infer0) * 1000.0, 2),
        },
        "inference": infer_meta,
    }

    return (reply or "").strip(), turn_metrics
