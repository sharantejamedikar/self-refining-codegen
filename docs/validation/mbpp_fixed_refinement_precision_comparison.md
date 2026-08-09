# MBPP-427 fixed-k=5 full-precision result

## Result

The full-precision (`bfloat16`) Qwen2.5-Coder-7B-Instruct hybrid refinement
run forced all 427 sanitized MBPP problems through exactly five iterations:

- ever-solved `pass@1_refined_fixed = 352/427 = 0.8244`;
- final-iteration-only `pass@1_refined_fixed_final = 334/427 = 0.7822`;
- generation calls: `2,135` (`427 * 5`);
- wall-clock: `4,573.2323` seconds (76 minutes 13.23 seconds);
- prompt tokens: `444,702`;
- completion tokens: `119,901`;
- total tokens: `564,603`.

All 427 persisted problem records contain exactly five iterations. The
ever-solved metric counts a problem if any iteration passed; the final-only
diagnostic counts only iteration 5.

## Adaptive-stopping comparison

The matching full-precision adaptive run solved exactly the same 352/427
problems (`0.8244`) using 647 calls. There were **zero paired ever-solved
outcome flips**: fixed-k recovered none of the 75 adaptive failures and lost
none under the protocol's ever-solved metric.

| Mode | Ever solved | Final-only | Calls | Total tokens | Wall-clock |
|---|---:|---:|---:|---:|---:|
| Adaptive | 352/427 = 0.8244 | 352/427 = 0.8244 | 647 | 206,160 | 1,505.8236 s |
| Fixed-k=5 | 352/427 = 0.8244 | 334/427 = 0.7822 | 2,135 | 564,603 | 4,573.2323 s |
| Fixed/adaptive | 0 problems | -18 problems | 3.30x | 2.74x | 3.04x |

Fixed-k therefore spent 1,488 additional generation calls without gaining an
ever-solved task. It used 3.30 times the calls, 2.74 times the tokens, and
3.04 times the wall-clock of adaptive stopping.

Forced iteration was harmful under final-only evaluation. Eighteen tasks
passed at least once before iteration 5 and failed at iteration 5:

| Problem | Five-iteration trajectory | Last pass | Final category |
|---|---:|---:|---|
| MBPP/91 | `FPFPF` | 4 | edge-case |
| MBPP/249 | `FPFPF` | 4 | edge-case |
| MBPP/252 | `FFFPF` | 4 | logic |
| MBPP/259 | `FPFPF` | 4 | logic |
| MBPP/265 | `FPFPF` | 4 | logic |
| MBPP/290 | `FPFFF` | 2 | logic |
| MBPP/391 | `FPFPF` | 4 | logic |
| MBPP/393 | `FPFPF` | 4 | logic |
| MBPP/429 | `FFPFF` | 3 | logic |
| MBPP/437 | `FPFPF` | 4 | logic |
| MBPP/475 | `FFPFF` | 3 | logic |
| MBPP/592 | `PFFFF` | 1 | logic |
| MBPP/595 | `FPFPF` | 4 | edge-case |
| MBPP/596 | `FPFPF` | 4 | logic |
| MBPP/624 | `FPFPF` | 4 | logic |
| MBPP/722 | `FPFPF` | 4 | edge-case |
| MBPP/750 | `FPFPF` | 4 | logic |
| MBPP/776 | `FPFPF` | 4 | edge-case |

`P` denotes a passing iteration and `F` a failing iteration. Fourteen of the
18 last passed at iteration 4, two at iteration 3, one at iteration 2, and one
at iteration 1; MBPP/290 also passed at iteration 2 after failing initially,
giving 18 cases total. The final failures comprise 13 logic and 5 edge-case
classifications. In every case, the feedback after a successful iteration was
`All assertions passed.`, yet the next prompt still asked for a corrected
complete solution. This reproduces the forced-iteration regression phenomenon
documented on HumanEval and in the Q4_K_M MBPP run. Eighteen is the largest
raw regression count among the four benchmark/configuration fixed-k runs, but
MBPP also contains substantially more tasks than HumanEval.

## Authoritative Q4_K_M comparison

The authoritative Q4_K_M fixed-k=5 run solved 350/427 ever (`0.8197`) and
337/427 at iteration 5 (`0.7892`), also using 2,135 calls. Full precision has
opposite observed directions under the two metric definitions:

| Precision/backend | Ever solved | Final-only | Calls | Regressions |
|---|---:|---:|---:|---:|
| Q4_K_M / Ollama | 350/427 = 0.8197 | 337/427 = 0.7892 | 2,135 | 13 |
| `bfloat16` / Hugging Face | 352/427 = 0.8244 | 334/427 = 0.7822 | 2,135 | 18 |
| Full-precision difference | +2/427 = +0.47 pp | -3/427 = -0.70 pp | 0 | +5 |

For ever-solved outcomes, full precision recovered 13 Q4_K_M failures and
lost 11 Q4_K_M successes, yielding its net two-problem advantage. At
iteration 5, it recovered 13 and lost 16, yielding the net three-problem
deficit. Six tasks regressed in both fixed runs: MBPP/249, /265, /393, /437,
/624, and /722.

This is an end-to-end configuration comparison, not a clean causal estimate
of quantization. Precision, inference backend, and hardware changed together
(Ollama/CPU Q4_K_M versus Hugging Face/CUDA `bfloat16`). The larger
full-precision regression count is descriptive of these two runs and does not
establish that precision caused the difference.

## Protocol and artifacts

The full-precision run used pinned model revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, the frozen 427-problem sanitized
MBPP set, seed 42, temperature 0.2, top-p 0.95, at most 512 new tokens per
call, repetition penalty 1.1, hybrid feedback, and the subprocess executor
with a 10-second timeout and 512 MiB memory limit. Fixed mode disabled success,
stagnation, and oscillation stopping until iteration 5.

- Full-precision fixed-k=5: [`20260809T162731.848774Z_cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full`](../../experiments/results/20260809T162731.848774Z_cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full/)
- Full-precision adaptive: [`20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full`](../../experiments/results/20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full/)
- Q4_K_M fixed-k=5: [`20260721T102049.383499Z_m7_quantized_local_development_hybrid_refinement_fixed_mbpp_full`](../../experiments/results/20260721T102049.383499Z_m7_quantized_local_development_hybrid_refinement_fixed_mbpp_full/)

The new artifact contains all 427 task IDs, exactly 2,135 persisted
iterations, its config snapshot, git commit, seeds, per-problem JSON, summary
CSV, and run summary.
