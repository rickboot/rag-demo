# RAG + Agentic Demo Plan — Phison aiDAPTIV

**Purpose:** One document to review before building.  
**Source:** Synthesized from planning chat (GTC credibility, engineer-grade, no hype).  
**Background:** [docs/ai_daptiv_canonical_overview.md](docs/ai_daptiv_canonical_overview.md) — canonical aiDAPTIV framing and value props.

---

## 1. What We’re Proving (Exact)

| Prove | Do not claim |
|-------|----------------|
| Memory limits break real AI workflows | Speed, magic, hype |
| aiDAPTIV removes that limit with acceptable trade-offs | “Unlimited memory,” “revolutionary” |

**Canonical framing:** Prevent OOM → longer sessions → persistent KV → larger effective working set.  
**One-liner:** “We’re not improving compute. We’re removing memory as the failure mode.”

---

## 1b. How This Demo Demonstrates Value (Three Failure Modes → One Fix)

Without aiDAPTIV, long RAG + agent sessions hit **three concrete failure modes**. The demo shows each one, then shows aiDAPTIV preventing them.

| Failure mode | What happens without aiDAPTIV | What the demo shows with aiDAPTIV |
|--------------|------------------------------|-----------------------------------|
| **OOM (out-of-memory)** | Process crashes; session lost. | No crash; session continues; evicted KV goes to flash instead of exhausting RAM. |
| **Catastrophic slowdown** | KV cache eviction forces **recompute** of evicted tokens; latency spikes badly (canonical: “retrieving from flash is significantly faster than recomputing”). | No eviction-induced recompute storm; evicted KV served from flash; latency stays usable (slight increase, not collapse). |
| **Context truncation** | System drops earlier context to fit the window; assistant “forgets” prior reasoning, files, scratchpad. Session degrades or resets. | Historical context retained (RAM + flash); no forced truncation; multi-step reasoning stays coherent. |

**Terms to use:** *Context truncation* (or *forced truncation*) = when the system drops earlier tokens/context to stay within the fixed window; the assistant effectively “forgets.” aiDAPTIV avoids that by extending effective context via flash.

**One-sentence value summary:** The demo proves aiDAPTIV **prevents OOM, prevents eviction-induced slowdown, and prevents context truncation** — so the coding assistant can run long sessions to completion instead of crashing, stalling, or forgetting.

---

## 2. Locked Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Corpus** | Hugging Face Transformers repo | Max recognition at GTC; large, real, no explanation needed |
| **Runtime** | vLLM | Production-grade; KV behavior is real |
| **Orchestration** | LangGraph | Stateful, production-aligned; better for agentic + memory growth than Haystack |
| **Vector DB** | FAISS (or Milvus) | Well-known, engineer-respected |
| **Demo hardware** | DGX Spark (GB10, 128GB unified DDR) | Constrained enough to hit limits; not “infinite” HBM |
| **Demo model** | 70B, 8-bit | Credible “no need to compromise on quant” story with aiDAPTIV |
| **Context** | 32K (or 64K if supported) | Realistic for serious dev use |
| **Pre-demo** | Pre-ingest only; no live embedding at GTC | Standard RAG practice; reduces risk and noise |

---

## 2b. Hardware Tiers (Dev vs Test vs Demo)

Use a **smaller model on dev**, then scale up on test/demo hardware so the same code path runs everywhere.

| Tier | Hardware | Model recommendation | Purpose |
|------|----------|----------------------|---------|
| **Dev** | MacBook Air M4, 16GB unified | **7B–8B** (e.g. Llama 3.2 8B, Qwen 7B), 4-bit if needed. Use Ollama or MLX on Mac; or point backend at a small vLLM instance. | Build and debug pipeline, RAG, LangGraph agent; no need for 70B locally. |
| **Test** | PC, RTX 5070 Ti, 16GB VRAM | **13B–34B** 4-bit (or 8-bit for 13B). Fits in 16GB with room for KV; can stress memory with long context or concurrency. | Validate failure behavior and telemetry before DGX Spark. |
| **Demo** | DGX Spark, 128GB unified | **70B 8-bit**, 32K context | Full “no compromise” story; OOM/truncation without aiDAPTIV, stability with it. |

**Config:** Use env or config to switch model name, context length, and inference URL by tier (e.g. `DEV_MODEL`, `TEST_MODEL`, `DEMO_MODEL`) so one codebase runs on all three.

---

## 3. Target Architecture (Minimal, Auditable)

```
Client (UI)
    ↓
FastAPI backend
    ↓
LangGraph agent (stateful, multi-step)
    ↓
Retriever (FAISS) ← pre-built index
    ↓
vLLM inference server (70B 8-bit)
    ↓
DGX Spark (128GB unified)
```

- No extra frameworks; every layer recognizable.
- aiDAPTIV integration at runtime/memory tier (KV eviction to flash).

---

## 4. Real-World Scenario (GTC Story)

- **Scenario:** Coding assistant over the Transformers codebase.
- **Task example:** “Trace generation_config behavior across model classes and propose a unified refactor.”
- **Why it works:** Multi-file retrieval, scratchpad growth, iterative reasoning → natural KV and context growth. No artificial prompt stuffing.

**60-second credibility pitch (use as script):**

- “This is not a synthetic demo. We’re running a standard production stack: vLLM serving a 70B-class model (8-bit), FAISS for retrieval, LangGraph for stateful agent. The dataset is the full Hugging Face Transformers repo — chunked normally, no tricks. We’re not modifying the runtime or forcing memory pressure artificially; this is default KV behavior under long sessions and multi-step reasoning. On this hardware, without aiDAPTIV, the session eventually fails — OOM or context truncation. With aiDAPTIV we don’t change the model or framework; we extend effective memory so KV eviction goes to flash. Session continues. You’ll see telemetry: memory, KV growth, flash hits. Slight latency increase; no crash; same hardware. I can share the repo and workload so you can reproduce it.”

---

## 5. Pre-Demo Prep (Repo Ingest)

- **Clone:** `huggingface/transformers` (optionally exclude tests/docs for controlled size).
- **Chunking:** 600–1000 tokens (e.g. 800), 10–20% overlap; respect function/class boundaries; preserve file paths.
- **Embeddings:** Credible model (e.g. bge-large-en or HF equivalent); GPU batch; persist to FAISS.
- **Expect:** ~30k–80k chunks; index on the order of hundreds of MB.
- **When:** All done ahead of GTC; load index at demo time. No live ingest.

**Ingest time (reference):** On 5080 mobile / Mobile Pro 5000 / DGX Spark: order of minutes, not hours.

---

## 6. Demo Flow (Live)

1. **Pre-demo framing (60–90 s)**  
   - Stack: vLLM, LangGraph, FAISS, Transformers repo (e.g. “XXk files, XXk chunks, XX MB index”).  
   - Scenario: “Coding assistant over Transformers — trace/refactor task.”

2. **Baseline (without aiDAPTIV)**  
   - Start assistant; multi-step task.  
   - Show telemetry (unified memory, KV growth, session length).  
   - Let session run until: OOM, severe slowdown, truncation, or reset.  
   - Message: “Typical — we ran out of memory headroom; model is fine.”

3. **With aiDAPTIV**  
   - Same hardware, model, index, workflow.  
   - “We’re not changing model or framework; we’re extending effective memory.”  
   - Run same scenario; session continues; no crash; show telemetry (including flash/tier usage).  
   - Acknowledge: slight latency tradeoff.

4. **Close**  
   - “Developers often go to 4-bit because of memory limits. Here we run 70B 8-bit and let a real workload grow without forcing compression or session resets.”

5. **Optional**  
   - Add a second concurrent coding session to show concurrency multiplier (enterprise angle).

---

## 7. Metrics (Engineer-Grade)

Show explicitly; avoid “faster” or vague claims.

| Metric | Without aiDAPTIV | With aiDAPTIV |
|--------|-------------------|----------------|
| Max session steps before failure | X | 3–5X (or “no hard failure”) |
| KV cache usable size | VRAM-only | Extended (flash) |
| OOM events | Yes | No |
| Context truncation | Yes | No |
| Total tokens in session | Lower | Higher |
| Completion | Partial | Full |

Optional: tokens/sec delta, latency delta, cache hit/miss. Be transparent about tradeoffs.

---

## 8. Failure Design (Without aiDAPTIV)

- **Goal:** Failure mid-task, not instant or random.
- **Levers:**  
  - Single long session (e.g. 20–30 steps), and/or  
  - 2 concurrent sessions, and/or  
  - 32K (or 64K) context.
- **Important:** Validate failure behavior *before* building full UI (see build order below).

On 128GB unified (DGX Spark): 70B 8-bit + long context + multi-step (and optionally 2 sessions) should produce real pressure.

---

## 9. Build Phases (Order)

Build in this order; validate failure before investing in full app.

| Phase | What | Success criteria |
|-------|------|-------------------|
| **1** | Inference first | vLLM serving 70B 8-bit stably on DGX Spark |
| **2** | Failure validation | Long synthetic session → reproducible memory ceiling / OOM or truncation |
| **3** | Repo ingest | Clone Transformers → chunk → embed → FAISS; know file/chunk counts and index size |
| **4** | RAG retrieval | Clean file-level retrieval over FAISS; no live embed |
| **5** | LangGraph agent | Stateful multi-step loop (plan → retrieve → analyze → refine → …); scratchpad grows |
| **6** | Telemetry | Unified memory, KV growth (if available), context length, session steps, optional: flash hits |
| **7** | Stress run | Single long run (and optionally 2 concurrent) to confirm failure without aiDAPTIV |
| **8** | aiDAPTIV enable | Same workload with aiDAPTIV; session continues; document tradeoffs |

**Rule:** Do not build full demo UI before confirming failure behavior (Phases 1–2, then 7).

---

## 10. Repo Structure (Suggested)

Keep layout minimal and auditable:

- **Backend:** FastAPI app, LangGraph agent, FAISS loader, vLLM client.
- **Ingest:** Script(s) for clone → chunk → embed → save FAISS (+ metadata).
- **Telemetry:** Service or module that gathers memory/KV/session metrics and exposes to UI or logs.
- **Config:** Model name, context length, quant, paths to index and repo (subset) — so the run is reproducible.
- **Docs:** README with stack, hardware, and “how to run / how to reproduce” (and link to public repo if applicable).

---

## 11. Credibility Checklist (Non-Negotiable)

- [ ] Stack is standard (vLLM, LangGraph, FAISS; no custom inference hacks).
- [ ] Workload is realistic (real repo, normal chunking, real coding task).
- [ ] Failure is reproducible (document steps and config).
- [ ] Tradeoffs stated (e.g. latency with aiDAPTIV).
- [ ] Repo public (or at least reproducible from shared instructions).
- [ ] Telemetry visible (memory, KV, session length, optional flash).

---

## 12. What Not To Do

- Do not claim “AI rewrites vLLM / singularity” — focus on memory stability.
- Do not embed at demo time; do not artificially inflate prompts.
- Do not pre-script a single “crash moment”; let failure emerge from real workload.
- Do not overstack frameworks (e.g. Haystack + LlamaIndex + LangChain + custom).
- Do not overstate quality gains (8-bit vs 4-bit: “more stable / less compression,” not “much better accuracy”).

---

## 13. Open Questions / Next Decisions

1. **Exact vLLM flags** for 70B 8-bit, 32K context, and max use of 128GB (and any aiDAPTIV-related options if applicable).
2. **KV visibility:** How to get KV cache size (or proxy) from vLLM for telemetry.
3. **aiDAPTIV integration:** Exact API or config to “enable” and to observe flash/tier usage for telemetry.
4. **Subset vs full repo:** Full Transformers vs exclude tests/docs — decide based on ingest time and stress target.
5. **Concurrency:** Whether to always demo 2 sessions or only as optional phase.

---

## 14. Summary

- **Prove:** Memory limits break real workflows; aiDAPTIV extends memory and avoids that failure.
- **Stack:** vLLM + LangGraph + FAISS + Transformers repo; 70B 8-bit; DGX Spark.
- **Flow:** Pre-ingest → explain stack and scenario → run without aiDAPTIV to failure → run with aiDAPTIV to success → show metrics and tradeoffs.
- **Build:** Inference → validate failure → ingest → RAG → agent → telemetry → stress run → aiDAPTIV.

Once you’re happy with this plan, next step is to break Phase 1–2 into concrete tasks (e.g. exact commands, env, and success checks) and then implement.
