# Phased Implementation Plan

Build in small steps so you can **run and play with the app after each phase**. Same codebase scales from Mac dev → 5070 Ti test → DGX Spark demo.

---

## Phase 1: Scaffold + “Hello” app

**Goal:** Repo structure, config, and a minimal app you can run in the browser.

| Task | Details |
|------|---------|
| Repo layout | `backend/`, `ingest/`, `frontend/` (or `ui/`), `config/`, `docs/` |
| Config | `.env.example` + config module: `INFERENCE_URL`, `MODEL_NAME`, `CONTEXT_LENGTH`, `TIER=dev|test|demo`, paths for index/repo |
| Backend | FastAPI app: `GET /health`, `GET /` or `GET /api/hello` returning something like `{"status":"ok","tier":"dev"}` |
| Frontend | Single HTML page (or minimal React/Vite) that calls the backend and shows the response; use [Pascari colors](docs/UI_COLOR_SCHEME.md) |
| Run | `uv run backend` (or `python -m backend`), open frontend in browser |

**You can play:** Open the app, see “Hello” and health check; confirm backend and frontend talk.

✅ **Phase 1 done.** Run: `uv sync && uv run python -m backend`, then open http://localhost:8000

---

## Phase 2: Inference wired (dev model)

**Goal:** Backend calls an LLM; you can send a prompt and see a reply.

| Task | Details |
|------|---------|
| Inference client | Backend module that calls the inference endpoint (Ollama on Mac, or vLLM later). Abstract behind an interface so we can swap URL/model. |
| Dev default | Mac: Ollama with 7B–8B (e.g. `llama3.2:8b`). `INFERENCE_URL=http://localhost:11434` or similar. |
| API | `POST /api/complete` or `POST /api/chat`: body `{ "prompt" }` or `{ "messages" }`, return model output. |
| UI | Input box + “Send”; display model response. No RAG yet. |

**You can play:** Type a question, get an LLM answer. Full “chat with model” on your Mac.

✅ **Phase 2 done.** Ensure Ollama is running (`ollama run llama3.1:8b` or your chosen model). Use the chat input and Send to get a reply.

---

## Phase 3: Ingest pipeline

**Goal:** Transformers repo → chunks → embeddings → FAISS index on disk. No UI change.

| Task | Details |
|------|---------|
| Clone | Script or doc: clone `huggingface/transformers`, optional exclude (e.g. tests/docs) for faster dev. |
| Chunking | 800 tokens, ~15% overlap, respect file boundaries; keep file path + range in metadata. |
| Embed | Use e.g. `sentence-transformers` or HF pipeline (bge-large-en or similar); batch; run on CPU or MPS on Mac. |
| FAISS | Build index, save to `config.INDEX_PATH`; save metadata (path, chunk index) alongside. |
| Docs | Log file count, chunk count, index size; document how to run ingest. |

**You can play:** Run ingest; inspect index (e.g. small script that loads FAISS and runs one query). Index is ready for Phase 4.

✅ **Phase 3 done.** Run: `uv run python -m ingest`. Uses `REPO_PATH` (default `./data/transformers`) and `INDEX_PATH` (default `./data/faiss_index`). First run clones Hugging Face Transformers and downloads `BAAI/bge-small-en-v1.5`; then chunks (800 tokens, 15% overlap) and builds FAISS + metadata.

---

## Phase 4: RAG retrieval in the app

**Goal:** Backend loads FAISS; API takes a query and returns retrieved chunks. UI lets you search the corpus.

| Task | Details |
|------|---------|
| Load index | Backend loads FAISS + metadata at startup (or on first use) from `INDEX_PATH`. |
| Embed query | Same embedding model as ingest; embed user query. |
| API | `POST /api/retrieve`: body `{ "query", "top_k": 10 }`, return chunks with file path, text, score. |
| UI | “Search Transformers corpus” box; show top chunks (file, snippet). Still no agent. |

**You can play:** Search the Transformers codebase from the app; see retrieved code chunks. Real RAG retrieval.

✅ **Phase 4 done.** Run ingest first (`uv run python -m ingest`), then start the backend. Use “Search Transformers corpus” in the UI; results show file path, snippet, and score.

---

## Phase 5: LangGraph agent (RAG + agent loop)

**Goal:** “Coding assistant”: user asks a question → agent retrieves chunks → calls LLM with context → returns answer. Single-turn first, then multi-turn.

| Task | Details |
|------|---------|
| Agent graph | LangGraph: start → retrieve (query + FAISS) → build prompt with chunks → call LLM → reply. Optional: plan → retrieve → analyze → refine loop. |
| State | Session state: conversation history (messages) + optional scratchpad. Store in memory first (per session id). |
| API | `POST /api/chat` or `POST /api/ask`: body `{ "message", "session_id" }`; agent runs retrieve + LLM; return assistant message. |
| UI | “Ask the coding assistant” (about Transformers code); show assistant reply; same session_id for follow-ups. |

**You can play:** Ask the assistant questions about the Transformers repo; get answers grounded in retrieved code; multi-turn conversation.

✅ **Phase 5 done.** Chat uses RAG: retrieve → prompt with context + history → LLM. Session state in memory; send `session_id` for multi-turn. UI shows "Coding assistant (RAG)" and conversation history. (Explicit agent loop in `backend/agent.py`; LangGraph can be layered on later.)

---

## Phase 6: Session persistence + telemetry

**Goal:** Longer conversations and visible metrics so you can see memory/session growth.

| Task | Details |
|------|---------|
| Session | Keep full message history in context (no aggressive summarization); optional scratchpad in state. Session identified by `session_id`. |
| Telemetry | Backend collects: session message count, total tokens in session (if available), approximate context length. Optional: `psutil` for process memory (dev). |
| API | `GET /api/session/:id` or include in chat response: `{ "session_id", "message_count", "metrics": { ... } }`. |
| UI | Show “Session: N messages” and simple metrics (e.g. memory, steps). Use Pascari colors. |

**You can play:** Long multi-turn session; watch message count and metrics grow. Prep for “this would OOM without aiDAPTIV” story.

✅ **Phase 6 done.** Backend collects session telemetry: `message_count`, `context_chars`; optional `process_rss_mb` when `psutil` is installed (`uv sync --extra dev`). Chat response includes `message_count` and `metrics`; `GET /api/session/:id` returns session metrics. UI shows “Session: N messages”, context chars, and memory (Pascari styling).

---

## Phase 7: Stress run + failure validation (test PC)

**Goal:** Run on 5070 Ti with larger model; confirm OOM or truncation without aiDAPTIV.

| Task | Details |
|------|---------|
| Test config | `TIER=test`, vLLM 13B or 34B (4-bit) on 5070 Ti; same backend/frontend, different `INFERENCE_URL` + model. |
| Stress | Long session (20–30 turns) or 2 concurrent sessions; don’t truncate aggressively. |
| Observe | Log OOM, truncation, or severe latency; capture telemetry. |
| Docs | Document “without aiDAPTIV” behavior; reproducible steps. |

**You can play:** Reproduce failure on test hardware; validate demo narrative before DGX Spark.

---

## Phase 8: Demo hardware + aiDAPTIV (DGX Spark)

**Goal:** Same app on DGX Spark; 70B 8-bit; enable aiDAPTIV; show session completes.

| Task | Details |
|------|---------|
| Demo config | `TIER=demo`, vLLM 70B 8-bit, 32K context; aiDAPTIV enabled per Phison integration. |
| Run | Same workload that failed in Phase 7; session continues; no OOM; optional second concurrent session. |
| Telemetry | Expose memory tier usage / flash hits if available; show in UI or logs. |
| Docs | Document tradeoffs (latency vs capability); “how to reproduce” for GTC. |

**You can play:** Full demo: before (failure) vs after (aiDAPTIV, stable).

---

## Summary: what you can do after each phase

| Phase | You can… |
|-------|----------|
| 1 | Run app in browser; see health / hello. |
| 2 | Chat with the LLM (no RAG). |
| 3 | Run ingest; have a FAISS index. |
| 4 | Search the Transformers corpus in the UI. |
| 5 | Use the coding assistant (RAG + agent). |
| 6 | Have long sessions with visible metrics. |
| 7 | Reproduce failure on 5070 Ti. |
| 8 | Run full demo on DGX Spark with aiDAPTIV. |

---

## Dependencies between phases

- **1 → 2:** Backend must run before wiring inference.
- **2 → 5:** LLM client needed before agent.
- **3 → 4:** Index must exist before retrieval.
- **4 → 5:** Retrieval is input to agent.
- **5 → 6:** Agent state is extended with telemetry.
- **6 → 7, 8:** Same app and config; only hardware and tier change.

Phases 3 (ingest) and 4 (RAG) can be developed in parallel with 2 (inference) once the scaffold is in place; the “play” order above keeps each phase runnable and testable.
