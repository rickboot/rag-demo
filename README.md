# RAG + Agentic Demo — Phison aiDAPTIV

A production-style RAG + agentic coding assistant demo that shows how **Phison aiDAPTIV+** memory extension prevents real AI workflow failures. Built for engineer credibility (vLLM, LangGraph, FAISS, Hugging Face Transformers corpus).

---

## How This Demo Demonstrates Value (Three Failure Modes → One Fix)

Without aiDAPTIV, long RAG + agent sessions can hit **three concrete failure modes**. The demo is designed to show each one, then show aiDAPTIV preventing them.

| Failure mode | What happens without aiDAPTIV | What the demo shows with aiDAPTIV |
|--------------|------------------------------|-----------------------------------|
| **OOM (out-of-memory)** | Process crashes; session lost. | No crash; session continues; evicted KV goes to flash instead of exhausting RAM. |
| **Catastrophic slowdown** | KV cache eviction forces **recompute** of evicted tokens; latency spikes badly (canonical: “retrieving from flash is significantly faster than recomputing”). | No eviction-induced recompute storm; evicted KV served from flash; latency stays usable (slight increase, not collapse). |
| **Context truncation** | System drops earlier context to fit the window; assistant “forgets” prior reasoning, files, scratchpad. Session degrades or resets. | Historical context retained (RAM + flash); no forced truncation; multi-step reasoning stays coherent. |

**Terms:** *Context truncation* (or *forced truncation*) = when the system drops earlier tokens/context to stay within the fixed window; the assistant effectively “forgets.” aiDAPTIV avoids that by extending effective context via flash.

**One-sentence value summary:** The demo is intended to show that aiDAPTIV **prevents OOM, eviction-induced slowdown, and context truncation** — so the coding assistant can run long sessions to completion.

**How the value props are actually demonstrated.** This repo (Phases 1–6) is the **same app** you run in two scenarios; the app by itself does not prove the table above. **Phase 7:** Run the app on constrained hardware (e.g. 5070 Ti) with a larger model and long or concurrent sessions — *observe* OOM, severe latency, or truncation ("without aiDAPTIV"). **Phase 8:** Run the same app on demo hardware (e.g. DGX Spark) with aiDAPTIV enabled and the same workload — *observe* no crash, stable latency, retained context ("with aiDAPTIV"). So the value props are demonstrated by **before/after runs** (different hardware and aiDAPTIV on/off), not by the code alone. See **IMPLEMENTATION_PLAN.md** (Phases 7–8) and **DEMO_PLAN.md** for the runbook.

---

## Run (Phase 1)

```bash
# From repo root
cp .env.example .env   # optional: edit TIER, INFERENCE_URL, etc.
uv sync
uv run python -m backend
```

Then open **http://localhost:8000** in your browser. You should see the Pascari-styled page and a backend “OK” response with tier and config.

**Phase 2 (chat):** Install and start the [Ollama app](https://ollama.com), then `ollama run llama3.1:8b`. See [docs/OLLAMA_SETUP.md](docs/OLLAMA_SETUP.md) if the CLI says it can’t find Ollama.

**Phase 3 (ingest):** Build the FAISS index from the Transformers repo: `uv run python -m ingest`. By default only the first 500 files are indexed (~1–2 min). Set `INGEST_MAX_FILES=0` in `.env` for a full-repo index (~20 min). First run clones the repo and downloads the embedding model; output: `data/faiss_index/index.faiss` and `metadata.json` (or `INDEX_PATH` from `.env`).

**Phase 4 (RAG search):** With the index built, the UI has “Search Transformers corpus”: type a query and see top-k chunks (file path, snippet, score). First search loads the index and embedding model (may take a few seconds).

**Phase 5 (coding assistant):** The "Coding assistant (RAG)" chat retrieves relevant chunks for each message, then calls the LLM with that context and conversation history. Multi-turn: backend keeps session state by `session_id` (sent automatically by the UI).

**Phase 6 (session metrics):** Each chat response includes session telemetry (message count, context size). The UI shows “Session: N messages”, context chars, and process memory (if `psutil` is installed: `uv sync --extra dev`). `GET /api/session/:id` returns session metrics.

---

## Docs

- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** — Phased build: each phase ends with a runnable app you can play with (scaffold → inference → ingest → RAG → agent → telemetry → stress → aiDAPTIV).
- **[NEXT_STEPS.md](NEXT_STEPS.md)** — What to do next: scaffold, ingest, then DGX Spark phases.
- **[DEMO_PLAN.md](DEMO_PLAN.md)** — Full plan: architecture, stack, demo flow, build phases, metrics, credibility checklist.
- **[docs/ai_daptiv_canonical_overview.md](docs/ai_daptiv_canonical_overview.md)** — Canonical aiDAPTIV background, value props, and messaging guardrails.
- **[docs/UI_COLOR_SCHEME.md](docs/UI_COLOR_SCHEME.md)** — Phison Pascari UI palette (yellow `#FFDD00`, blue `#1C3051`, white) and usage for the demo UI.
- **[docs/M4_16GB_DEGRADATION.md](docs/M4_16GB_DEGRADATION.md)** — Model/quant and prompts to get “perform well, then degrade” on MacBook Air M4 16GB.
