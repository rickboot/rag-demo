"""Run Degradation Test: predefined multi-turn sequence against existing RAG + chat."""

from config import settings

from backend.agent import run_rag_chat

DEGRADATION_PROMPTS = [
    "Explain how generation_config flows through the Transformers codebase.",
    "List the primary files involved and describe their responsibilities.",
    "Trace how beam search parameters are validated and passed.",
    "Identify differences in how encoder-decoder vs causal models handle generation.",
    "List all call sites for generation utilities and explain behavioral differences.",
    "Propose a unified abstraction to reduce duplication.",
    "Show where backward compatibility constraints would block this change.",
    "If we modify generation_config validation, which tests would break?",
    "Trace downstream impacts on Trainer.",
    "Does this change affect gradient checkpointing logic?",
    "Summarize our proposed change so far.",
    "Modify the proposal to maintain backward compatibility.",
    "List all files referenced so far.",
    "Reconcile earlier proposal with encoder-decoder differences.",
    "Provide a full patch plan across modules.",
]
NUM_DEGRADATION_TURNS = len(DEGRADATION_PROMPTS)


def _metrics_from_turn(turn: int, _prompt: str, _response: str, turn_metrics: dict) -> dict:
    inf = turn_metrics.get("inference") or {}
    rag = turn_metrics.get("rag") or {}
    timing = turn_metrics.get("timing_ms") or {}
    sizes = turn_metrics.get("sizes") or {}
    prompt_tokens = inf.get("prompt_eval_count")
    completion_tokens = inf.get("eval_count")
    if prompt_tokens is None:
        prompt_tokens = 0
    if completion_tokens is None:
        completion_tokens = 0
    total_tokens = prompt_tokens + completion_tokens
    retrieved = rag.get("returned", 0)
    paths = rag.get("paths") or []
    unique_files = len({p for p in paths if p})
    history_turns = sizes.get("history_messages", 0)  # before this turn
    latency_ms = (timing.get("retrieve_ms") or 0) + (timing.get("inference_ms") or 0)
    # Context size for this turn = prompt tokens sent to model (grows with history)
    context_tokens = prompt_tokens
    # KV cache size not provided by Ollama; optional placeholder for vLLM/other backends
    kv_cache_mb = None
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "context_tokens": context_tokens,
        "kv_cache_mb": kv_cache_mb,
        "retrieved_chunks": retrieved,
        "unique_files": unique_files,
        "history_turns": history_turns,
        "latency_ms": round(latency_ms, 2),
    }


async def run_degradation_test(session_id: str, history_store: dict) -> dict:
    """
    Run the predefined 15-turn prompt sequence using existing RAG + chat.
    Reuses session_id and appends to history in history_store[session_id].
    Returns structured result with turns and final_memory_stats.
    """
    if session_id not in history_store:
        history_store[session_id] = []
    history = history_store[session_id]
    turns_out = []
    peak_memory_mb = None

    for turn_num, prompt in enumerate(DEGRADATION_PROMPTS, 1):
        try:
            reply, turn_metrics = await run_rag_chat(prompt, history)
            history.append({"role": "user", "content": prompt})
            history.append({"role": "assistant", "content": reply})
            metrics = _metrics_from_turn(turn_num, prompt, reply, turn_metrics)
            turns_out.append({
                "turn": turn_num,
                "prompt": prompt,
                "response": reply,
                "metrics": metrics,
            })
            try:
                import psutil
                mb = psutil.Process().memory_info().rss / (1024 * 1024)
                if peak_memory_mb is None or mb > peak_memory_mb:
                    peak_memory_mb = round(mb, 2)
            except Exception:
                pass
        except Exception as e:
            turns_out.append({
                "turn": turn_num,
                "prompt": prompt,
                "response": f"[Error: {e!s}]",
                "metrics": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "context_tokens": 0,
                    "kv_cache_mb": None,
                    "retrieved_chunks": 0,
                    "unique_files": 0,
                    "history_turns": len(history) // 2,
                    "latency_ms": 0,
                },
            })

    final_memory = _session_metrics_for_degradation(history)
    final_memory_stats = {
        "peak_memory": peak_memory_mb,
        "kv_cache_size": None,
    }
    if final_memory.get("process_rss_mb") is not None:
        final_memory_stats["final_rss_mb"] = final_memory["process_rss_mb"]

    return {
        "session_id": session_id,
        "turns": turns_out,
        "final_memory_stats": final_memory_stats,
    }


def _session_metrics_for_degradation(_history: list) -> dict:
    try:
        import psutil
        proc = psutil.Process()
        return {"process_rss_mb": round(proc.memory_info().rss / (1024 * 1024), 2)}
    except Exception:
        return {}


async def run_degradation_turn(
    session_id: str | None,
    prompt_index: int,
    history_store: dict,
) -> dict:
    """
    Run one degradation turn: prompt = DEGRADATION_PROMPTS[prompt_index].
    Returns { session_id, turn, prompt, response, metrics }.
    """
    if not (0 <= prompt_index < len(DEGRADATION_PROMPTS)):
        raise ValueError(f"prompt_index must be 0..{len(DEGRADATION_PROMPTS) - 1}")
    import uuid
    sid = (session_id or "").strip() or str(uuid.uuid4())
    if sid not in history_store:
        history_store[sid] = []
    history = history_store[sid]
    prompt = DEGRADATION_PROMPTS[prompt_index]
    turn_num = prompt_index + 1
    try:
        reply, turn_metrics = await run_rag_chat(prompt, history)
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": reply})
        metrics = _metrics_from_turn(turn_num, prompt, reply, turn_metrics)
        return {
            "session_id": sid,
            "turn": turn_num,
            "prompt": prompt,
            "response": reply,
            "metrics": metrics,
            "model": settings.model_name,
        }
    except Exception as e:
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": f"[Error: {e!s}]"})
        return {
            "session_id": sid,
            "turn": turn_num,
            "prompt": prompt,
            "response": f"[Error: {e!s}]",
            "metrics": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "context_tokens": 0,
                "kv_cache_mb": None,
                "retrieved_chunks": 0,
                "unique_files": 0,
                "history_turns": (len(history) - 2) // 2,
                "latency_ms": 0,
            },
            "model": settings.model_name,
        }
