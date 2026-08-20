# Dissertation results tables: Tier 1, Tier 2, and Tier 3

These tables are the citation-ready presentation of the frozen Tier 1 results
for `Qwen/Qwen2.5-Coder-7B-Instruct` at pinned revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, run through Hugging Face/CUDA in
`bfloat16`. HumanEval contains 164 problems and the sanitized MBPP split
contains 427. The frozen master summary is commit `859cd66`.[^master]

The reported problem-level score counts a problem as solved when any candidate
permitted by the method passes all tests. Thus the fixed-​*k* row uses its
ever-solved score; its final-iteration-only diagnostic is reported separately
in Table 3. “Compute ratio” is generation calls divided by the corresponding
best-of-5 call count, so lower values indicate fewer model calls.

The cross-model replication in Tables 5 and 6 adds
`codellama/CodeLlama-13b-Instruct-hf` on both benchmarks. CodeLlama used
bitsandbytes 8-bit quantization, whereas Qwen used full-precision
`bfloat16`. Consequently, the cross-model results are an end-to-end
configuration comparison, not a precision-controlled estimate of model-family
effects. The complete frozen matrix contains 16 configurations: four methods
for each model-benchmark pair.

## Table 1. Main Tier 1 results

| Benchmark | Configuration | pass@1 (solved/total) | Generation calls | Compute ratio vs best-of-5 | Source |
|---|---|---:|---:|---:|---:|
| HumanEval-164 | Single-pass | 0.8659 (142/164) | 164 | 0.2000× | H-S[^h-s] |
| HumanEval-164 | Best-of-5 | **0.9268 (152/164)** | 820 | 1.0000× | H-B[^h-b] |
| HumanEval-164 | Adaptive hybrid refinement | 0.9024 (148/164) | **199** | **0.2427×** | H-A[^h-a] |
| HumanEval-164 | Fixed-​*k*=5 hybrid refinement (ever solved) | 0.9024 (148/164) | 820 | 1.0000× | H-F[^h-f] |
| MBPP-427 | Single-pass | 0.7190 (307/427) | 427 | 0.2000× | M-S[^m-s] |
| MBPP-427 | Best-of-5 | 0.7892 (337/427) | 2,135 | 1.0000× | M-B[^m-b] |
| MBPP-427 | Adaptive hybrid refinement | **0.8244 (352/427)** | **647** | **0.3030×** | M-A[^m-a] |
| MBPP-427 | Fixed-​*k*=5 hybrid refinement (ever solved) | **0.8244 (352/427)** | 2,135 | 1.0000× | M-F[^m-f] |

**Table note.** Bold marks the highest problem-level score within a benchmark
and, among tied refinement scores, the lower call count. Best-of-5 uses five
independent samples at temperature 0.8. Both refinement configurations use
temperature 0.2 and permit at most five iterations; only the adaptive variant
applies success, stagnation, and oscillation stopping.

## Table 2. Central compute-matched comparison

| Benchmark | Best-of-5 pass@1 | Adaptive-refinement pass@1 | Refinement difference | Calls: best-of-5 → refinement | Refinement call ratio | Calls saved | Source |
|---|---:|---:|---:|---:|---:|---:|---:|
| HumanEval-164 | 0.9268 (152/164) | 0.9024 (148/164) | −4 problems (−2.44 pp) | 820 → 199 | 0.2427× (4.12× fewer) | 621 (75.73%) | H-B + H-A[^h-b][^h-a] |
| MBPP-427 | 0.7892 (337/427) | **0.8244 (352/427)** | **+15 problems (+3.51 pp)** | 2,135 → 647 | **0.3030× (3.30× fewer)** | **1,488 (69.70%)** | M-B + M-A[^m-b][^m-a] |

**Table note.** This is the dissertation’s headline comparison. Both methods
have the same maximum allowance of five model generations per problem, but
adaptive refinement can stop early. On HumanEval, refinement used substantially
less compute but did not match best-of-5 accuracy. On MBPP, it was both more
accurate and more call-efficient.

## Table 3. Convergence ablation

| Benchmark | Adaptive ever solved | Fixed-​*k* ever solved | Fixed-​*k* final-only | Adaptive calls | Fixed-​*k* calls | Extra fixed calls | Fixed-​*k* regressions | Source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HumanEval-164 | 0.9024 (148/164) | 0.9024 (148/164) | 0.8720 (143/164) | 199 | 820 | 621 (4.12× total) | 5 | H-A + H-F[^h-a][^h-f] |
| MBPP-427 | 0.8244 (352/427) | 0.8244 (352/427) | 0.7822 (334/427) | 647 | 2,135 | 1,488 (3.30× total) | 18 | M-A + M-F[^m-a][^m-f] |

**Table note.** “Ever solved” counts a task if any iteration passed;
“final-only” counts only iteration 5. A regression is an ever-solved fixed-​*k*
task whose fifth iteration failed. Fixed-​*k* recovered no additional task on
either benchmark relative to adaptive stopping, while forced continuation
created five HumanEval and 18 MBPP final-state regressions.

## Table 4. Key paired significance tests

| Benchmark | Paired comparison (first − second) | First-only | Second-only | Paired difference | Exact McNemar *p* | Significant at 0.05? | Source |
|---|---|---:|---:|---:|---:|---:|---:|
| HumanEval-164 | Adaptive refinement − best-of-5 | 3 | 7 | −4/164 (−2.44 pp) | 0.3438 | No | H-A + H-B[^h-a][^h-b] |
| MBPP-427 | Adaptive refinement − best-of-5 | 33 | 18 | +15/427 (+3.51 pp) | 0.0489 | Yes | M-A + M-B[^m-a][^m-b] |
| HumanEval-164 | Adaptive refinement − fixed-​*k* (ever solved) | 0 | 0 | 0/164 (0.00 pp) | 1.0000 | No | H-A + H-F[^h-a][^h-f] |
| MBPP-427 | Adaptive refinement − fixed-​*k* (ever solved) | 0 | 0 | 0/427 (0.00 pp) | 1.0000 | No | M-A + M-F[^m-a][^m-f] |

**Table note.** Values use the project’s pre-specified exact, two-sided,
conditional-binomial McNemar test with no continuity correction. P-values are
unadjusted. The adaptive-versus-fixed rows compare the headline ever-solved
outcome, for which the paired task outcomes are identical; final-only scores
are diagnostics and are not substituted for the pre-specified headline
metric.

## Table 5. Cross-model HumanEval-164 replication

| Configuration | Qwen full-precision pass@1 | Qwen calls | CodeLlama 8-bit pass@1 | CodeLlama calls | Source |
|---|---:|---:|---:|---:|---:|
| Single-pass | 0.8659 (142/164) | 164 | 0.4146 (68/164) | 164 | H-S + C-S[^h-s][^c-s] |
| Best-of-5 | **0.9268 (152/164)** | 820 | **0.6220 (102/164)** | 820 | H-B + C-B[^h-b][^c-b] |
| Adaptive hybrid refinement | 0.9024 (148/164) | **199** | 0.5305 (87/164) | **311** | H-A + C-A[^h-a][^c-a] |
| Fixed-​*k*=5 hybrid refinement (ever solved) | 0.9024 (148/164) | 820 | 0.5305 (87/164) | 820 | H-F + C-F[^h-f][^c-f] |
| Fixed-​*k*=5 hybrid refinement (final only) | 0.8720 (143/164) | 820 | 0.4756 (78/164) | 820 | H-F + C-F[^h-f][^c-f] |

**Table note.** Bold marks the highest headline score and the adaptive
refinement call count within each model configuration. Gap closure is defined
as `(adaptive solved − single-pass solved) / (best-of-5 solved − single-pass
solved)`. Adaptive refinement closed 60.0% of the Qwen gap (`6/10`) and 55.9%
of the CodeLlama gap (`19/34`). It used 75.73% fewer calls than best-of-5 for
Qwen and 62.07% fewer for CodeLlama.

The qualitative pattern replicated: for both model configurations,
execution-feedback refinement improved on single-pass generation and
approached best-of-5 while using substantially fewer calls. The quantitative
gap closure was weaker for the less capable CodeLlama configuration, and its
remaining best-of-5 deficit was larger: 15 problems (9.15 percentage points),
versus 4 problems (2.44 percentage points) for Qwen. This difference must not
be attributed solely to capability or model family because CodeLlama was
8-bit quantized while Qwen was full precision.

Forced-iteration regression also replicated across model families. Nine
CodeLlama tasks that passed before iteration 5 failed at the final iteration,
compared with five Qwen tasks. Using the fixed-run reporting denominators,
these are 9/87 (10.3%) and 5/143 (3.5%), respectively; the corresponding
ever-solved-to-final score changes are 87 to 78 and 148 to 143. This confirms
the existence of the phenomenon across the two model configurations and
supports success-priority stopping. It does not establish a model-specific
rate difference: there is only one run per configuration, and model family,
model size, and precision are confounded.[^cross-model]

## Table 6. Cross-model MBPP-427 replication

| Configuration | Qwen full-precision pass@1 | Qwen calls | CodeLlama 8-bit pass@1 | CodeLlama calls | Source |
|---|---:|---:|---:|---:|---:|
| Single-pass | 0.7190 (307/427) | 427 | 0.4496 (192/427) | 427 | M-S + C-M-S[^m-s][^c-m-s] |
| Best-of-5 | 0.7892 (337/427) | 2,135 | **0.6159 (263/427)** | 2,135 | M-B + C-M-B[^m-b][^c-m-b] |
| Adaptive hybrid refinement | **0.8244 (352/427)** | **647** | 0.6019 (257/427) | **821** | M-A + C-M-A[^m-a][^c-m-a] |
| Fixed-*k*=5 hybrid refinement (ever solved) | 0.8244 (352/427) | 2,135 | 0.6019 (257/427) | 2,135 | M-F + C-M-F[^m-f][^c-m-f] |
| Fixed-*k*=5 hybrid refinement (final only) | 0.7822 (334/427) | 2,135 | 0.4941 (211/427) | 2,135 | M-F + C-M-F[^m-f][^c-m-f] |

**Table note.** On CodeLlama, adaptive refinement improved on single-pass by
65 problems but trailed best-of-5 by six (1.41 percentage points), while using
61.55% fewer calls. Fixed continuation recovered no task beyond adaptive
stopping and produced 46 final-state regressions: 46/257 (17.90%) of tasks
ever solved in that run. All 46 exhibit the documented contradictory
post-success prompt pattern.[^c-m-fixed-analysis] As in Table 5, model family,
size, and precision are confounded, and each cell is one fixed-seed run.

## Table 7. Tier 3 Pro benchmark matrix

| Model configuration | Benchmark | Single-pass | Best-of-5 | Adaptive refinement | Fixed-*k*=5 refinement (ever solved) |
|---|---|---:|---:|---:|---:|
| Qwen full precision | HumanEval Pro-164 | 0.6524 (107/164) | **0.7866 (129/164)** | 0.7012 (115/164) | 0.7012 (115/164) |
| Qwen full precision | MBPP Pro-378 | 0.6032 (228/378) | **0.7646 (289/378)** | 0.6799 (257/378) | 0.6799 (257/378) |
| CodeLlama 8-bit | HumanEval Pro-164 | 0.2866 (47/164) | **0.4329 (71/164)** | 0.3354 (55/164) | 0.3354 (55/164) |
| CodeLlama 8-bit | MBPP Pro-378 | 0.3783 (143/378) | **0.5450 (206/378)** | 0.4630 (175/378) | 0.4630 (175/378) |

**Table note.** Tier 3 comprises 16 full-benchmark configurations: four
methods for each model-benchmark pair. Qwen used the pinned full-precision
`bfloat16` configuration and CodeLlama used the established bitsandbytes
8-bit replication configuration. Best-of-5 was the highest-scoring method in
all four Pro conditions. Adaptive refinement improved over single-pass in all
four, but did not match compute-matched best-of-5.[^pro-stats]

## Table 8. Tier 3 Pro convergence ablation

| Model configuration | Benchmark | Adaptive ever solved | Fixed-*k* ever solved | Fixed-*k* final-only | Adaptive calls | Fixed calls | Regressions |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen full precision | HumanEval Pro-164 | 115/164 | 115/164 | 114/164 | 256 | 820 | 1 |
| Qwen full precision | MBPP Pro-378 | 257/378 | 257/378 | 253/378 | 620 | 1,890 | 4 |
| CodeLlama 8-bit | HumanEval Pro-164 | 55/164 | 55/164 | 54/164 | 340 | 820 | 1 |
| CodeLlama 8-bit | MBPP Pro-378 | 175/378 | 175/378 | 164/378 | 718 | 1,890 | 11 |

**Table note.** Fixed continuation produced no ever-solved gain over adaptive
stopping in any Pro condition, while requiring the full five calls per task.
Its final iteration lost 17 previously solved task outcomes in total. The
regression count is the number of fixed-run tasks that passed at least once
but failed at iteration 5; it is computed directly from the committed
per-problem trajectories.

## Table 9. Tier 3 Pro paired statistical significance

| Model configuration | Benchmark | Paired comparison | First-only | Second-only | Paired difference | Exact McNemar *p* | Significant at 0.05? |
|---|---|---|---:|---:|---:|---:|---:|
| Qwen full precision | HumanEval Pro-164 | Adaptive − best-of-5 | 3 | 17 | −14/164 (−8.54 pp) | 0.00258 | Yes |
| Qwen full precision | MBPP Pro-378 | Adaptive − best-of-5 | 9 | 41 | −32/378 (−8.47 pp) | 5.61×10⁻⁶ | Yes |
| CodeLlama 8-bit | HumanEval Pro-164 | Adaptive − best-of-5 | 8 | 24 | −16/164 (−9.76 pp) | 0.00700 | Yes |
| CodeLlama 8-bit | MBPP Pro-378 | Adaptive − best-of-5 | 19 | 50 | −31/378 (−8.20 pp) | 0.000244 | Yes |
| Qwen full precision | HumanEval Pro-164 | Adaptive − fixed-*k* ever solved | 0 | 0 | 0/164 (0.00 pp) | 1.00000 | No |
| Qwen full precision | MBPP Pro-378 | Adaptive − fixed-*k* ever solved | 0 | 0 | 0/378 (0.00 pp) | 1.00000 | No |
| CodeLlama 8-bit | HumanEval Pro-164 | Adaptive − fixed-*k* ever solved | 0 | 0 | 0/164 (0.00 pp) | 1.00000 | No |
| CodeLlama 8-bit | MBPP Pro-378 | Adaptive − fixed-*k* ever solved | 0 | 0 | 0/378 (0.00 pp) | 1.00000 | No |

**Table note.** These are the pre-specified exact, two-sided conditional
binomial McNemar tests without continuity correction. P-values are unadjusted.
The requested Qwen headline results are *p*=0.00258 on HumanEval Pro and
*p*=5.61×10⁻⁶ on MBPP Pro. The committed statistical artifact also preserves
10,000-resample problem-level bootstrap confidence intervals and paired effect
sizes for all 16 configurations.[^pro-stats]

## Table 10. Tier 3 Qwen HumanEval-100 ablations

| Ablation axis | Setting | pass@1_refined | Model calls | Prompt tokens | Completion tokens | Wall-clock (s) | Convergence: success/oscillation/stagnation/max | Source |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Feedback-length cap | 100 words | 0.9300 (93/100) | 116 | 25,150 | 8,586 | 261.58 | 93/4/3/0 | Q-F100[^q-f100] |
| Feedback-length cap | 200 words | 0.9300 (93/100) | 116 | 25,150 | 8,586 | 259.34 | 93/4/3/0 | Q-F200[^q-f200] |
| Feedback-length cap | 300 words | 0.9300 (93/100) | 116 | 25,150 | 8,586 | 256.69 | 93/4/3/0 | Q-F300[^q-f300] |
| Refinement temperature | 0.0 | 0.9200 (92/100) | 122 | 27,966 | 9,261 | 274.14 | 92/5/3/0 | Q-T0[^q-t0] |
| Refinement temperature | 0.4 | 0.9100 (91/100) | 122 | 28,099 | 10,081 | 298.07 | 91/5/4/0 | Q-T04[^q-t04] |
| Refinement temperature | 0.8 | 0.9100 (91/100) | 122 | 28,700 | 11,028 | 325.14 | 91/3/6/0 | Q-T08[^q-t08] |

**Table note.** All six configurations use `humaneval_ablation_100`, a fixed,
stratified 100-task HumanEval subset, with seed 42 and adaptive hybrid
refinement. The Qwen feedback-length 100/200/300 configurations have identical
per-task pass/fail vectors.

## Table 11. Tier 3 CodeLlama HumanEval-100 ablations

| Ablation axis | Setting | pass@1_refined | Model calls | Prompt tokens | Completion tokens | Source |
|---|---:|---:|---:|---:|---:|---:|
| Feedback-length cap | 100 words | 0.5200 (52/100) | 187 | 58,162 | 15,412 | C-F100[^c-f100] |
| Feedback-length cap | 200 words | 0.5200 (52/100) | 187 | 58,162 | 15,412 | C-F200[^c-f200] |
| Feedback-length cap | 300 words | 0.5200 (52/100) | 187 | 58,162 | 15,412 | C-F300[^c-f300] |
| Refinement temperature | 0.0 | 0.5000 (50/100) | 190 | 59,700 | 14,582 | C-T0[^c-t0] |
| Refinement temperature | 0.4 | **0.5200 (52/100)** | 190 | 59,251 | 15,733 | C-T04[^c-t04] |
| Refinement temperature | 0.8 | 0.5000 (50/100) | 198 | 62,076 | 15,542 | C-T08[^c-t08] |

**Table note.** All six configurations use `humaneval_ablation_100`, the same
fixed, stratified 100-task HumanEval subset, with seed 42 and adaptive hybrid
refinement. The CodeLlama feedback-length 100/200/300 configurations have
identical per-task pass/fail vectors and token counts because observed feedback
did not reach the active cap. Temperature 0.4 matched the 0.2 reference
configuration at 52/100; temperatures 0.0 and 0.8 each solved 50/100. With one
fixed-seed run per cell, these results describe sensitivity within this
protocol rather than run-to-run variability.

The authoritative reporting total is **44 configurations**: 16 Tier 1/2 core
configurations, 16 Tier 3 Pro configurations, and 12 sensitivity
configurations. Development and validation runs are not part of these 44.

## Artifact and commit references

Every table entry above resolves to an immutable run directory. The commit is
the value persisted in that directory’s `git_commit.txt`; the linked directory
also contains the configuration snapshot, seeds, per-problem JSON, and summary
files.

[^master]: Master synthesis: git commit `859cd66`; [`docs/validation/full_precision_tier1_summary.md`](validation/full_precision_tier1_summary.md).
[^h-s]: **H-S:** git commit `8d6a1958c3f6fb443b9b3f6450d4c1989596cedd`; [`experiments/results/20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full/`](../experiments/results/20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full/).
[^h-b]: **H-B:** git commit `0c9984f4ac976a87d53fffc895efac06eb6c2e68`; [`experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/`](../experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/).
[^h-a]: **H-A:** git commit `43dd49387c0b8a42676d8503aaa664623b009aca`; [`experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/`](../experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/).
[^h-f]: **H-F:** git commit `3b6014e21929ff7d8ff71ffbc2c8a9135d05cd29`; [`experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/`](../experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/).
[^m-s]: **M-S:** git commit `24ecdf153f8bf7237267e3a8a8cc0b88c2501c7e`; [`experiments/results/20260809T100420.122030Z_cluster_qwen_hf_zero_shot_mbpp_full/`](../experiments/results/20260809T100420.122030Z_cluster_qwen_hf_zero_shot_mbpp_full/).
[^m-b]: **M-B:** git commit `195c24f6cadfdeb044d754fadbc50adec35f5fb1`; [`experiments/results/20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full/`](../experiments/results/20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full/).
[^m-a]: **M-A:** git commit `dae941e62195eca48d17f3884939f6e7aaa91bf2`; [`experiments/results/20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full/`](../experiments/results/20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full/).
[^m-f]: **M-F:** git commit `7507a422afb33f86256aa16bb0e926379e5477ef`; [`experiments/results/20260809T162731.848774Z_cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full/`](../experiments/results/20260809T162731.848774Z_cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full/).
[^c-s]: **C-S:** git commit `a855eb1ac9d08e05633af70e29e1232afced7eed`; [`experiments/results/20260810T113106.471817Z_cluster_codellama_13b_bnb_8bit_zero_shot_humaneval_full/`](../experiments/results/20260810T113106.471817Z_cluster_codellama_13b_bnb_8bit_zero_shot_humaneval_full/).
[^c-b]: **C-B:** git commit `6cb1deef5025d922dc86e0a4823116dc4c3daff1`; [`experiments/results/20260810T121044.505386Z_cluster_codellama_13b_bnb_8bit_best_of_5_humaneval_full/`](../experiments/results/20260810T121044.505386Z_cluster_codellama_13b_bnb_8bit_best_of_5_humaneval_full/).
[^c-a]: **C-A:** git commit `e5a829b5c10d4c8edde7f61eb87ff438c25f1d86`; [`experiments/results/20260810T164232.226049Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_full/`](../experiments/results/20260810T164232.226049Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_full/).
[^c-f]: **C-F:** git commit `1dfc96c9436db2a8f04dfb2d209004fee2d9a94a`; [`experiments/results/20260810T220239.789427Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_humaneval_full/`](../experiments/results/20260810T220239.789427Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_humaneval_full/).
[^c-m-s]: **C-M-S:** git commit `b24f31bc468c81706844aa4f01c4c376c15a9e37`; [`experiments/results/20260811T125007.528701Z_cluster_codellama_13b_bnb_8bit_zero_shot_mbpp_full/`](../experiments/results/20260811T125007.528701Z_cluster_codellama_13b_bnb_8bit_zero_shot_mbpp_full/).
[^c-m-b]: **C-M-B:** git commit `e95775a190342203dbedf6ff639fec5742ff82ea`; [`experiments/results/20260811T185140.732397Z_cluster_codellama_13b_bnb_8bit_best_of_5_mbpp_full/`](../experiments/results/20260811T185140.732397Z_cluster_codellama_13b_bnb_8bit_best_of_5_mbpp_full/).
[^c-m-a]: **C-M-A:** git commit `20b161898692443e3aa32b5c83338841beb4753b`; [`experiments/results/20260812T222900Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_mbpp_full/`](../experiments/results/20260812T222900Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_mbpp_full/).
[^c-m-f]: **C-M-F:** git commit `80bde190b03b441b7e2328b8b8475cd8353c440f`; [`experiments/results/20260813T005000Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_mbpp_full/`](../experiments/results/20260813T005000Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_mbpp_full/).
[^c-m-fixed-analysis]: Fixed-run validation: [`docs/validation/codellama_mbpp_fixed_refinement_analysis.md`](validation/codellama_mbpp_fixed_refinement_analysis.md).
[^q4-m-s]: **Q4-M-S:** [`experiments/results/20260716T171911.599683Z_m7_quantized_local_development_single_mbpp_full/`](../experiments/results/20260716T171911.599683Z_m7_quantized_local_development_single_mbpp_full/).
[^cross-model]: Cross-model synthesis: git commit `a5d1574`; [`docs/validation/cross_model_summary.md`](validation/cross_model_summary.md).
[^pro-stats]: Tier 3 statistics and run mapping: git commit `cc815fc`; [`docs/validation/tier3_pro_statistics.json`](validation/tier3_pro_statistics.json).
[^q-f100]: [`experiments/results/20260814T025440.309834Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_feedback_100/`](../experiments/results/20260814T025440.309834Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_feedback_100/).
[^q-f200]: [`experiments/results/20260814T025910.954271Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_feedback_200/`](../experiments/results/20260814T025910.954271Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_feedback_200/).
[^q-f300]: [`experiments/results/20260814T030339.239970Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_feedback_300/`](../experiments/results/20260814T030339.239970Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_feedback_300/).
[^q-t0]: [`experiments/results/20260814T030804.958684Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_temperature_0p0/`](../experiments/results/20260814T030804.958684Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_temperature_0p0/).
[^q-t04]: [`experiments/results/20260814T031248.190945Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_temperature_0p4/`](../experiments/results/20260814T031248.190945Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_temperature_0p4/).
[^q-t08]: [`experiments/results/20260814T031755.254502Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_temperature_0p8/`](../experiments/results/20260814T031755.254502Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_temperature_0p8/).
[^c-f100]: [`experiments/results/20260814T202408.473726Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_feedback_100/`](../experiments/results/20260814T202408.473726Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_feedback_100/).
[^c-f200]: [`experiments/results/20260814T205744.788552Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_feedback_200/`](../experiments/results/20260814T205744.788552Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_feedback_200/).
[^c-f300]: [`experiments/results/20260814T213135.886361Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_feedback_300/`](../experiments/results/20260814T213135.886361Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_feedback_300/).
[^c-t0]: [`experiments/results/20260814T221627.451262Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_temperature_0p0/`](../experiments/results/20260814T221627.451262Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_temperature_0p0/).
[^c-t04]: [`experiments/results/20260814T224910.453589Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_temperature_0p4/`](../experiments/results/20260814T224910.453589Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_temperature_0p4/).
[^c-t08]: [`experiments/results/20260814T232441.662230Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_temperature_0p8/`](../experiments/results/20260814T232441.662230Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_temperature_0p8/).
