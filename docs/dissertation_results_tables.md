# Dissertation results tables: Tier 1 and cross-model replication

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
