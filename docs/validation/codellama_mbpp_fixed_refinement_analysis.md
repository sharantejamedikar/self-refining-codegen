# CodeLlama-13B 8-bit fixed-k refinement on MBPP-427

## Result

The fixed-`k=5` hybrid-refinement run completed all 427 sanitized MBPP tasks.
Its protocol metric (success at any iteration) was unchanged from adaptive
stopping, but its iteration-5-only diagnostic was substantially lower:

| Metric | Fixed `k=5` | Adaptive | Fixed/adaptive |
|---|---:|---:|---:|
| Ever solved | 257/427 = 0.6019 | 257/427 = 0.6019 | 0 tasks |
| Iteration-5-only | 211/427 = 0.4941 | Not applicable | -46 from fixed ever-solved |
| Model calls | 2,135 | 821 | 2.60x; +1,314 |
| Total tokens | 777,571 | 309,044 | 2.52x; +468,527 |
| Summed wall clock | 18,916.06 s | 8,039.95 s | 2.35x; +10,876.11 s |

The fixed and adaptive ever-solved task sets are exactly identical: there are
zero fixed-only and zero adaptive-only successes. Fixed iteration therefore
used 160.05% more model calls, 151.61% more tokens, and 135.28% more summed
wall-clock time for zero ever-solved gain. Calls are counted from the 427
persisted records, each of which contains exactly five iterations
(`427 * 5 = 2,135`); they are not inferred from the expected protocol alone.

## Forced-iteration regressions

A regression is an ever-solved task that passed before iteration 5 and failed
at iteration 5. There are **46**, or 46/257 = **17.90%** of the fixed run's
ever-solved tasks. `P` and `F` below denote persisted success and failure at
iterations 1 through 5.

| Trajectory | Regression task IDs |
|---|---|
| `FPFPF` | MBPP/6, /11, /68, /116, /128, /248, /249, /251, /266, /290, /294, /393, /431, /446, /475, /477, /577, /606, /624, /629, /741 |
| `PFFFF` | MBPP/308, /389, /411, /443, /455, /476, /580, /610, /754, /797 |
| `FFPFF` | MBPP/14, /87, /310 |
| `FPFFF` | MBPP/69, /439, /778, /801 |
| `FFFPF` | MBPP/595, /755 |
| `PFPPF` | MBPP/232, /732 |
| `PPFFF` | MBPP/96 |
| `PFPFF` | MBPP/102 |
| `FFPPF` | MBPP/400 |
| `FPPFF` | MBPP/644 |

The last passing iteration was iteration 4 for 26 cases, iteration 1 for 10,
iteration 2 for 5, and iteration 3 for 5. Their iteration-5 classifier outcomes
were logic for 25, edge-case for 13, and runtime for 8. Thus CodeLlama extends
the previously observed logic/edge-case mutations with executable failures
that raise at runtime.

## Contradictory post-success prompt

All 46 cases reproduce the same prompt defect documented in the other five
fixed-run conditions. The persisted feedback on the last successful iteration
contains `All assertions passed.` The immediately following rendered user
prompt contains that success feedback and then `Return a corrected complete
solution.` This was checked in both persisted fields (`feedback` on the last
passing iteration and `generation.rendered_user_prompt` on the next iteration)
for 46/46 regressions. No failing assertion or traceback justified another
repair. The result is consistent with uninformed post-success mutation caused
by continuing after success while presupposing that the successful program
needs correction.

## Evidence and interpretation

The authoritative fixed artifact is
[`20260813...fixed_mbpp`](../../experiments/results/20260813T005000Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_mbpp_full/),
at git commit `80bde190b03b441b7e2328b8b8475cd8353c440f`. The matching adaptive artifact
is [`20260812...adaptive_mbpp`](../../experiments/results/20260812T222900Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_mbpp_full/).
All figures were recomputed from their per-problem JSON; generated code was not
re-executed.

This is the sixth fixed-run condition and completes coverage of the two models
and two benchmarks in the executed experiment matrix (with Qwen additionally
represented by full precision and Q4_K_M). It is an independent
problem-run/configuration condition, not 46 independent causal trials: all
tasks use one fixed seed and the same feedback template.
