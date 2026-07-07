# AGENTS.md — Self-Refining Code Generation (Master's Dissertation)

> This file is the single source of truth for this project. Read it fully before any work.
> If anything you're asked to do conflicts with this file, stop and ask.

## 1. Project

**Title:** Self-Refining Code Generation Using Execution Feedback
**Research question:** Can LLMs improve code generation through iterative refinement using execution feedback, and which error categories (syntax, runtime, logic, edge-case, timeout) are amenable to automated self-correction?
**Stakes:** Master's dissertation, hard deadline **September 1, 2026**. Grade matters — rigor over flash.
**Owner:** Sharan (student). You are the senior ML engineer + research advisor pair-programming this with him.

## 2. Non-negotiable decisions (do not re-litigate; flag concerns once, then comply)

1. **Models:**
   - Primary: `Qwen/Qwen2.5-Coder-7B-Instruct` — all experiments.
   - Replication (Tier 2): `codellama/CodeLlama-13b-Instruct-hf` — cross-family generality claim.
   - Local dev uses **4-bit quantized Qwen** (MLX or Ollama on Apple Silicon). All *reported* numbers come from full-precision GPU runs. Quantization used in dev must be documented.
   - Pin exact HF revision hashes in config for reproducibility.
2. **Benchmarks:** HumanEval (164) + MBPP (500, sanitized split) primary. HumanEval Pro + MBPP Pro are Tier 3 only.
3. **Baselines — the core of the contribution:**
   - (a) Single-pass pass@1.
   - (b) **Compute-matched best-of-k sampling** (k=5 independent samples, temperature 0.8 for diversity; a problem counts as solved if ANY candidate passes all tests).
   - (c) Full refinement system (≤5 iterations).
   - Every headline claim compares (c) against (b), not just (a). This is non-negotiable.
4. **Refinement loop:** generate → sandboxed execute → error classification → feedback → regenerate. Max 5 iterations.
5. **Convergence criteria (in priority order):** success (100% tests pass) → max iterations (k=5) → stagnation (patience=2: unchanged pass rate + identical error-message hash) → oscillation (exact code-hash match within last 3 iterations).
6. **Feedback strategies (ablation axis):** template-based, trace-based, hybrid (rule-based selector by error type).
7. **Error taxonomy:** syntax, runtime, logic (assertion failure), edge-case (partial test failure), timeout. Classification is deterministic code, not LLM-judged.
8. **Statistics:** McNemar's test for paired configuration comparisons; bootstrap 95% CIs (10,000 resamples) on pass@1; report effect sizes. Per-problem results persisted as JSON so all stats are recomputable offline.
9. **Sandboxing:** subprocess-based first (resource limits, timeout, no network, temp dir). Docker hardening is a later milestone, never a blocker. All execution goes through one `Executor` interface so backends are swappable.
10. **Generation hyperparameters:** refinement/single-pass use temperature=0.2, top_p=0.95, max_new_tokens=512, repetition_penalty=1.1. Best-of-k sampling uses temperature=0.8. Fixed seeds everywhere; seeds recorded in results JSON.

## 3. Tiered experiment plan (build the pipeline once; tiers are configs)

- **Tier 1 (must run on MacBook alone if the cluster never arrives):** Qwen-7B on full HumanEval + MBPP, baselines (a)(b)(c), convergence ablation (adaptive stopping vs fixed k=5).
- **Tier 2:** CodeLlama-13B replication of Tier 1 headline; feedback-strategy ablation (template/trace/hybrid) on 100 stratified HumanEval problems; error taxonomy on 50 failures.
- **Tier 3:** HumanEval Pro + MBPP Pro (both models); feedback-length ablation (100/200/300 words); temperature sweep if time.
- **Contingency (pre-decided):** if HTCondor access is unconfirmed by **July 17, 2026**, Tier 2 moves to Colab Pro; Tier 3 shrinks to Qwen-only HumanEval Pro. Do not silently drop anything else.

## 4. Repository structure

```
self-refining-codegen/
├── CLAUDE.md
├── configs/            # YAML: model, dataset, experiment, device (mac|cluster|colab)
├── src/
│   ├── data/           # loaders, validation, dev-split creation
│   ├── generation/     # model wrapper (HF/MLX/Ollama backends), prompt builders, code extraction
│   ├── execution/      # Executor interface; SubprocessExecutor; (later) DockerExecutor
│   ├── feedback/       # error classifier; template/trace/hybrid feedback generators
│   ├── convergence/    # ConvergenceDetector + IterationRecord
│   ├── loop/           # orchestrator: refinement loop, best-of-k runner, single-pass runner
│   ├── analysis/       # stats (McNemar, bootstrap), tables, plots
│   └── utils/          # logging, hashing, seeding, io
├── experiments/
│   ├── scripts/        # one entry script per experiment, config-driven
│   └── results/        # JSON per problem, one dir per experiment run (timestamped)
├── tests/              # pytest, mirrors src/
├── notebooks/          # analysis only, never core logic
└── data/               # datasets (gitignored)
```

## 5. Coding standards

- Python 3.10. Type hints on all public functions. Docstrings on all modules/classes.
- `black` + `ruff` clean before every commit. Small, focused commits with descriptive messages.
- Config-driven everything (YAML + a typed config dataclass). No hardcoded paths, model names, or hyperparameters in logic.
- Device auto-detection: CUDA → MPS → CPU, overridable in config. Every script must run unmodified on MacBook, cluster, and Colab.
- **Mock LLM backend** (`MockGenerator` returning canned outputs) so the entire pipeline and all tests run without a model or GPU. Tests never require model downloads.
- pytest for every module; target >85% coverage on `src/`. Integration test: full loop on 3 problems with the mock backend.
- Structured logging: every iteration logs code, execution result, feedback, convergence decision, timing → one JSON per problem per run.

## 6. Experiment protocol

- Dev sets first, always: HumanEval-Dev (20 stratified) and MBPP-Dev (50 stratified). **Full sets are touched only for final, frozen runs** — never during development or debugging.
- Every run directory contains: config snapshot, git commit hash, seeds, per-problem JSON, and a summary CSV.
- Metrics definitions (use these exact names):
  - `pass@1_single`: fraction solved by one generation.
  - `pass@1_bo5`: fraction solved by best-of-5 sampling.
  - `pass@1_refined`: fraction solved within ≤5 refinement iterations.
  - Plus: iterations-to-success distribution, convergence-reason distribution, error-category transition counts across iterations, wall-clock and token cost per configuration.
- Dataset validation on load: canonical solutions must pass their own tests; `ast.parse` on all code; log and quarantine any broken problems (do not silently fix or drop).

## 7. Guardrails — read carefully

1. **Never fabricate numbers.** No placeholder results, no "expected" accuracies written as if measured. If a run hasn't executed, say so.
2. **Never claim tests pass without running them.** Paste the actual pytest output.
3. **No silent stubs.** If you stub something to keep moving, it must raise `NotImplementedError` or be a clearly named mock, and you must list it in your end-of-session summary.
4. **Ask before:** changing architecture/interfaces in section 2-4, adding heavy dependencies, deleting data or results, or any operation on the full benchmark sets.
5. **Working end-to-end before optimization.** No caching layers, batching, or container pooling until the loop produces correct results on dev sets.
6. **Generated code is untrusted.** It only ever runs inside the Executor sandbox — never `exec`/`eval` in the main process, including in tests.
7. End every session with: what was built, what was tested (with output), what is stubbed/incomplete, and the recommended next task.

## 8. Milestones (work strictly in order; each has a definition of done)

- **M1 — Skeleton runs:** repo scaffold, configs, dataset loader + validation, dev splits, SubprocessExecutor, MockGenerator, single-pass runner. DoD: one HumanEval problem flows generate→execute→pass/fail with the mock; all tests green.
- **M2 — Real model:** Qwen backend (quantized local), code extraction robust to markdown/prose output, `pass@1_single` on HumanEval-Dev. DoD: a real measured dev-set baseline number with results JSON.
- **M3 — Refinement loop:** error classifier, template feedback, ConvergenceDetector, orchestrator. DoD: `pass@1_refined` > `pass@1_single` on dev set, or a documented investigation of why not.
- **M4 — Fair baseline:** best-of-5 runner. DoD: all three metrics on both dev sets in one comparison table.
- **M5 — Feedback strategies:** trace-based + hybrid generators. DoD: three-way dev-set comparison.
- **M6 — Stats + hardening:** McNemar, bootstrap CIs, plots; Docker executor if environment allows. DoD: analysis notebook reproduces all numbers from stored JSON alone.
- **M7 — Tier 1 full runs.** M8 — Tier 2. M9 — Tier 3 + error taxonomy support tooling.

## 9. Hardware context

- MacBook Pro M4 Pro, **24GB unified memory** — 4-bit 7B only; never load 13B or full-precision 7B locally.
- HTCondor GPU cluster: requested, pending. Docker support unknown — hence the Executor abstraction.
- Colab Pro: fallback for GPU runs.
