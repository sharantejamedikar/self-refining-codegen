# M7 Tier 1 full-run preflight — stopped before execution

**Time:** 2026-07-15 19:19 IST (`2026-07-15T13:49:15Z`)  
**Git commit:** `35d2e2002874e2b9085b0bd2b035b2217f91ad6a`  
**Initial worktree:** clean  
**Outcome:** no full benchmark run was started

The M7 request explicitly required execution only and instructed the operator to stop
rather than make a judgment call or improvise a fix. Preflight found the following
blocking mismatches between the request and the committed execution surface.

## Verified inputs and resources

- `data/normalized/humaneval.jsonl`: 164 records.
- `data/normalized/mbpp_sanitized.jsonl`: 427 records.
- Disk at preflight: 699 GiB available (22% volume utilization).
- Memory at preflight: 24 GiB installed; `memory_pressure` reported 69% system-wide
  memory free, zero swap-ins, and zero swap-outs.
- The committed model configs use Qwen2.5-Coder-7B-Instruct through Ollama with
  `Q4_K_M` quantization and seed 42.

## Blocking findings

1. **No committed full-set M7 configs exist.** Every current Qwen single-pass,
   best-of-five, and refinement config has `split: dev` and points to either
   `data/dev/humaneval_dev.jsonl` or `data/dev/mbpp_dev.jsonl`. Launching the full
   normalized paths would require creating new configs and deciding their names,
   feedback strategy, profile, and provenance before execution.

2. **Fixed-five refinement is not implemented as a selectable mode.** The typed
   `ExperimentConfig` has no adaptive/fixed stopping field. `RefinementRunner` always
   calls `ConvergenceDetector`, and the detector always stops on success, stagnation,
   or oscillation before the maximum where applicable. Therefore the requested
   adaptive-versus-fixed-`k=5` convergence ablation cannot be run through the committed
   config surface.

3. **M5 did not identify one uniformly best feedback strategy.** Template refinement
   scored best on HumanEval-Dev, while trace/hybrid scored best on MBPP-Dev. Selecting
   hybrid globally, template/hybrid per benchmark, or another policy would change the
   experimental interpretation and needs an explicit decision.

4. **The available execution profile is quantized local development, not
   full-precision reporting.** `AGENTS.md` requires dissertation-reported numbers to
   come from full-precision GPU runs. The current committed Qwen configs select the
   local Ollama `Q4_K_M` artifact. Direction is needed on whether this overnight run is
   an explicitly labeled quantized contingency/development full-set run or must wait
   for a full-precision GPU environment.

5. **All three current runners persist per-problem records only after the entire run
   finishes.** `SinglePassRunner`, `BestOfKRunner`, and `RefinementRunner` each first
   compute every record in a list comprehension and only then write the per-problem
   JSON files. A crash or safety stop can therefore lose completed in-memory problems,
   which is at odds with the requested preference for honest partial overnight
   results. Changing this behavior would be a code change, prohibited by the
   execution-only instruction.

## Decisions required before launch

1. Authorize and review committed M7 full-set configs.
2. Define and implement/test the fixed-five stopping semantics before the ablation.
   In particular, clarify whether a solved candidate still triggers four additional
   generations, and what feedback is supplied after success.
3. Choose one feedback policy explicitly: global hybrid, or template for HumanEval and
   hybrid for MBPP, or another predeclared rule.
4. Specify local quantized versus full-precision GPU execution status.
5. Accept batched persistence risk or authorize incremental per-problem checkpointing
   before unattended full runs.

No result directory was created and no model endpoint was contacted during this
preflight.

The unchanged committed test suite was run after preflight: `88 passed in 1.69s`.
