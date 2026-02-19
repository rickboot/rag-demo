# Run “perform well, then degrade” on MacBook Air M4 16GB

This doc suggests **model/quant** and **prompts** so the app runs well at first, then visibly degrades (slower latency, growing memory, or context pressure) so you can observe the effect without aiDAPTIV.

---

## 0. Fast then degrade (recommended if 8B feels slow)

If each response takes ~50s and everything feels degraded, use a **faster default** so early turns are clearly fast, then latency grows as the run continues.

### Option F — Small model, fast start, then degrade

In `.env`:

```env
MODEL_NAME=phi3:mini
NUM_CTX=2048
RAG_TOP_K=4
MAX_CONTEXT_CHARS=6000
```

- **phi3:mini** (~3.8B) is much faster than 8B on M4. Pull with: `ollama pull phi3:mini`
- **NUM_CTX=2048** keeps the context window small so prompt processing stays fast; later turns will hit the limit (truncation) or you'll see latency rise as history grows.
- **RAG_TOP_K=4** and **MAX_CONTEXT_CHARS=6000** shrink the prompt so each turn is quicker.

**Result:** Early turns (e.g. 1–5) are fast (often &lt;10s). Later turns slow down as context grows → clear "fast then degrade."

### Option G — Keep 8B but speed it up

If you prefer to stay on `llama3.1:8b`:

```env
MODEL_NAME=llama3.1:8b
NUM_CTX=2048
NUM_PREDICT=512
RAG_TOP_K=4
MAX_CONTEXT_CHARS=6000
```

- **NUM_CTX=2048** reduces KV work per turn (faster than default 8K).
- **NUM_PREDICT=512** caps reply length so generation finishes sooner.
- Smaller RAG context = smaller prompts = faster.

Early turns will be faster than with default 8B; later turns still degrade as history grows.

---

## 1. Model and quantization

**Goal:** Use a model that fits in 16GB and is fast for a few turns, then degrades as the session grows (longer prompts, more history).

### Option A — Gradual degradation (recommended)

- **Model:** `llama3.1:8b` (default).
- **Quant:** Default in Ollama is usually Q4 or similar; no change needed.
- **In .env:** `MODEL_NAME=llama3.1:8b` (or leave unset).

**Why it works:** 8B fits comfortably. Early turns are fast. As you run more turns (or the **Run Degradation Test**), prompt size and history grow → **latency and token counts rise**. You see “perform well then degrade” as **throughput/latency** degrades, not OOM.

**Pull if needed:** `ollama pull llama3.1:8b`

### Option B — Push toward OOM / heavy swap

- **Model:** A 13B model at 4-bit, e.g. `llama3.1:13b` or `mistral:13b` (if available in Ollama).
- **In .env:** `MODEL_NAME=llama3.1:13b` (or the tag Ollama uses).

**Why it might degrade more:** 13B 4-bit uses ~7–8GB for weights; with OS, RAG (embedding model + FAISS), and browser you can hit 16GB. Long multi-turn sessions can then cause swap or OOM. Early turns may be fine; later turns slow down or fail.

**Caveat:** On M4 16GB, 13B 4-bit might still fit; degradation may show as **slowdown** rather than hard OOM. If you never see OOM, Option A is more reliable for “perform well then degrade” (latency growth).

---

## 2. Prompts that cause degradation

**Use the built-in Run Degradation Test** (sidebar → “Run Degradation Test”). It runs 15 turns with prompts that:

- Ask for explanations, lists, and traces (long answers).
- Reuse and extend the same conversation (history grows every turn).
- Are ordered so context and prompt size grow steadily.

That alone will make **prompt tokens and latency** rise over turns on M4 16GB with `llama3.1:8b`.

### If you want to stress more (manual chat)

Use long, multi-turn prompts so each reply is large and history blows up faster, for example:

1. “Explain how generation_config flows through the Transformers codebase and list every file that touches it.”
2. “For each of those files, list the main functions and how they use generation_config.”
3. “Trace beam search validation end-to-end and include code snippets for each step.”
4. “Summarize everything we’ve discussed so far in full.”
5. Repeat “summarize everything so far” every few turns to force long context.

Combined with **Option A** (8B), you should see:

- **Early turns:** Low latency, modest prompt tokens.
- **Later turns:** Higher latency, prompt tokens and (where available) context size growing in the sidebar metrics.

---

## 3. What to look for (metrics)

- **Sidebar → Current session:** Message count, context chars, memory (if `psutil` is installed).
- **Sidebar → Run Degradation Test:** After a run, check:
  - **Metrics table:** `prompt_tokens`, `latency_ms`, `history_turns` increasing over turns.
  - **Charts:** “Prompt tokens vs turn” and “Retrieved chunks vs turn” trending up or flat while latency grows.

That pattern = **perform well (early turns), then degrade (later turns)** on M4 16GB without changing model config.

---

## 4. Quick reference

| Goal                  | Model / quant      | Prompts / flow                          |
|-----------------------|--------------------|-----------------------------------------|
| Gradual degradation   | `llama3.1:8b`      | Run Degradation Test (15 turns)         |
| Stronger stress      | Same 8B            | Manual long multi-turn + “summarize so far” |
| Try OOM / swap        | `llama3.1:13b` 4-bit (if fits) | Run Degradation Test or long manual chat |

Use **Option A + Run Degradation Test** for a reproducible “perform well, then degrade” on your MacBook Air M4 16GB.
