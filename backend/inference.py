"""Inference client: Ollama (dev) or vLLM (test/demo). Swap via config."""

import httpx

from config import settings


async def generate(prompt: str) -> tuple[str, dict]:
    """
    Send prompt to the configured inference endpoint; return (reply, telemetry).

    For Ollama /api/generate, the response often includes useful counters like:
    - prompt_eval_count, eval_count
    - total_duration, prompt_eval_duration, eval_duration (ns)
    """
    import time

    url = f"{settings.inference_url}/api/generate"
    payload = {
        "model": settings.model_name,
        "prompt": prompt,
        "stream": False,
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    t1 = time.perf_counter()

    reply = (data.get("response", "") or "").strip()
    telemetry = {
        "model": settings.model_name,
        "http_ms": round((t1 - t0) * 1000.0, 2),
    }
    # Pass through Ollama metrics if present (safe to ignore downstream).
    for k in (
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "prompt_eval_duration",
        "eval_count",
        "eval_duration",
        "created_at",
        "done",
        "done_reason",
    ):
        if k in data:
            telemetry[k] = data[k]
    return reply, telemetry


async def complete(prompt: str) -> str:
    """
    Send prompt to the configured inference endpoint; return model reply.
    Uses Ollama API when INFERENCE_URL points at Ollama (e.g. http://localhost:11434).
    """
    reply, _telemetry = await generate(prompt)
    return reply
