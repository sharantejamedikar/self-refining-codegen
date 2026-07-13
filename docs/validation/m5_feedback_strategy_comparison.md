# M5 feedback-strategy comparison

**Run date:** 2026-07-14  
**Implementation commit:** `0903acae8d31b97589e293a0c55b9be7fe3a3f8b`  
**Model:** Qwen2.5-Coder-7B-Instruct, local Ollama `Q4_K_M` development artifact  
**Scope:** frozen HumanEval-Dev (20) and MBPP-Dev (50) splits

These are quantized local development results, not dissertation-reported full-precision
GPU results. All three strategies used the same seed, generation hyperparameters,
subprocess limits, and sandbox trace collection. The first-iteration candidate code was
identical across strategies for every problem in both splits, so observed differences
begin only after feedback.

## Results

| Benchmark | Template | Trace | Hybrid |
|---|---:|---:|---:|
| HumanEval-Dev | 19/20 (0.95) | 18/20 (0.90) | 18/20 (0.90) |
| MBPP-Dev | 39/50 (0.78) | 42/50 (0.84) | 42/50 (0.84) |

Trace and hybrid made no gains on HumanEval-Dev and both regressed on
HumanEval/83. On MBPP-Dev, both gained three solves with no losses relative to
template: MBPP/631, MBPP/734, and MBPP/742. Trace used 22,815 prompt tokens and
hybrid used 21,604, compared with 13,635 for template. Hybrid matched trace's
solve count while avoiding trace feedback for simple runtime failures.

## Named case studies

The task description calls these “five named case studies” but enumerates six; all six
are reported here.

| Case | Template | Trace | Hybrid | Before/after interpretation |
|---|---|---|---|---|
| HumanEval/46 | Failed; oscillation at iteration 2 | Failed; oscillation at iteration 2 | Failed; oscillation at iteration 2 | No change. Trace identified line 10 (`return d`) and repeated actual/expected divergences, but the model returned identical code. |
| HumanEval/75 | Passed at iteration 2 | Passed at iteration 2 | Passed at iteration 2 | Clean refinement win retained under all strategies. |
| HumanEval/83 | Passed at iteration 2 | Failed; oscillation at iteration 2 | Failed; oscillation at iteration 2 | Regression. Trace identified the incorrect return expression, but the model repeated it; hybrid selected trace for the same edge-case failure. |
| MBPP/446 | Passed at iteration 2 | Passed at iteration 2 | Passed at iteration 2 | Clean output-shape/logic refinement win retained under all strategies. |
| MBPP/597 | Failed; oscillation at iteration 2 | Failed; oscillation at iteration 2 | Failed; oscillation at iteration 2 | No solve. Trace measured candidate recursion depth 998, identified the recursive return lines, and advised restructuring, but the model repeated identical code. Hybrid correctly treated `RecursionError` as complex runtime and selected trace. |
| MBPP/734 | Failed; regression then oscillation at iteration 3 | Passed at iteration 2 | Passed at iteration 2 | Trace/hybrid converted the prior failure into a clean refinement win by changing the weighted-sum loop to contiguous-subarray products. |

## Run artifacts

- HumanEval template: `experiments/results/20260713T222148.461537Z_m5_qwen_ollama_template_refinement_humaneval_dev`
- HumanEval trace: `experiments/results/20260713T222522.003946Z_m5_qwen_ollama_trace_refinement_humaneval_dev`
- HumanEval hybrid: `experiments/results/20260713T222718.512169Z_m5_qwen_ollama_hybrid_refinement_humaneval_dev`
- MBPP template: `experiments/results/20260713T222826.453953Z_m5_qwen_ollama_template_refinement_mbpp_dev`
- MBPP trace: `experiments/results/20260713T223141.925579Z_m5_qwen_ollama_trace_refinement_mbpp_dev`
- MBPP hybrid: `experiments/results/20260713T223538.251373Z_m5_qwen_ollama_hybrid_refinement_mbpp_dev`

## Interpretation

Richer trace feedback helped on the more varied MBPP failures but was not uniformly
beneficial. It increased prompt cost substantially, failed to break either focal
oscillation (HumanEval/46 and MBPP/597), and caused one HumanEval regression. The
hybrid rule preserved the same accuracy as trace on these dev sets with fewer prompt
tokens, supporting hybrid as the more efficient M5 strategy to carry forward. This is
a dev-set engineering conclusion, not a statistical generality claim; the planned
larger feedback-strategy ablation remains necessary.
