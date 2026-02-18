# Next Steps

Actionable order. Tied to [DEMO_PLAN.md](DEMO_PLAN.md) build phases.

**Phased plan:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — 8 phases; each phase ends with something you can run and play with.

**Hardware tiers:** Dev = MacBook Air M4 16GB (small model, e.g. 7B–8B). Test = PC 5070 Ti 16GB (13B–34B). Demo = DGX Spark 128GB (70B 8-bit). See DEMO_PLAN §2b.

---

## Right now (Mac M4 16GB — dev)

| Step | Action | Outcome |
|------|--------|---------|
| **Scaffold repo** | Add minimal dirs + files: `backend/`, `ingest/`, `frontend/` (or `ui/`), `config/`, env example. | Clear place for Phase 3–6 code. |
| **Config** | Add `config/` (or `.env.example`) with: model name, context length, quant, index path, repo path; support DEV/TEST/DEMO tiers (see DEMO_PLAN §2b). | Reproducible runs on dev, test, and demo. |
| **Ingest pipeline (Phase 3)** | Script: clone Transformers → chunk (800 tok, overlap) → embed (e.g. bge-large-en) → save FAISS + metadata. Run on any machine; persist index to disk. | Index ready to load on DGX Spark; can test with subset first. |
| **Resolve open questions** | Decide: full Transformers vs exclude tests/docs; document vLLM flags when known; note aiDAPTIV integration point when available. | Fewer blockers during build. |

---

## When test PC (5070 Ti 16GB) is available

| Step | Action | Outcome |
|------|--------|---------|
| **Phase 1 (test)** | Run vLLM with 13B or 34B (4-bit) on 5070 Ti. Same backend/agent code, larger model. | Validate memory pressure and telemetry on real GPU. |
| **Phase 2 (test)** | Long session or 2 concurrent; confirm OOM or truncation. | Failure story validated before demo hardware. |

---

## When DGX Spark (demo hardware) is available

| Step | Action | Outcome |
|------|--------|---------|
| **Phase 1** | Run vLLM serving 70B 8-bit, 32K context. Document exact launch command and env. | Inference stable; baseline for failure test. |
| **Phase 2** | Long synthetic session (no RAG yet): many steps or large context. Log memory; confirm OOM or truncation. | Reproducible failure; validates demo story. |
| **Phase 4** | Wire FAISS index into backend; implement file-level retrieval API. | RAG layer ready for agent. |
| **Phase 5** | Implement LangGraph agent (plan → retrieve → analyze → refine); stateful, scratchpad grows. | Agentic loop that grows KV. |
| **Phase 6** | Add telemetry: memory, session steps, context length; optional KV proxy if vLLM exposes it. | Metrics for live demo. |
| **Phase 7** | Stress run: same workload that failed in Phase 2, with RAG + agent. Confirm failure without aiDAPTIV. | Demo “before” is credible. |
| **Phase 8** | Enable aiDAPTIV; rerun; document tradeoffs and telemetry. | Demo “after”; story complete. |

---

## Suggested order this week

1. **Scaffold** — Create `backend/`, `ingest/`, `config/`, and a minimal `README`/config so the repo is build-ready.
2. **Ingest** — Implement and run the Transformers ingest pipeline (optionally on a subset) so the index exists and can be loaded later.
3. **Open questions** — Fill in vLLM flags and aiDAPTIV integration in `DEMO_PLAN.md` or `docs/` as you get answers (hardware, Phison SDK/docs).

If you say which you want to do first (scaffold, ingest, or open questions), we can break that into concrete tasks and start implementing.
