# Full-precision Tier 1 master results

## Complete matrix

This is the master reference table for the dissertation's Tier 1 results
chapter. It contains all eight frozen full-precision
Qwen2.5-Coder-7B-Instruct configurations: four methods on HumanEval-164 and
the same four on sanitized MBPP-427.

| Benchmark | Configuration | Full-precision accuracy | Calls | Q4_K_M accuracy | Q4_K_M calls | Full-precision vs Q4_K_M |
|---|---|---:|---:|---:|---:|---:|
| HumanEval-164 | Single-pass | 142/164 = 0.8659 | 164 | 136/164 = 0.8293 | 164 | +6 (+3.66 pp) |
| HumanEval-164 | Best-of-5 | 152/164 = 0.9268 | 820 | 150/164 = 0.9146 | 820 | +2 (+1.22 pp) |
| HumanEval-164 | Adaptive hybrid refinement | 148/164 = 0.9024 | 199 | 143/164 = 0.8720 | 202 | +5 (+3.05 pp); -3 calls |
| HumanEval-164 | Fixed-k=5 hybrid refinement | ever: 148/164 = 0.9024; final: 143/164 = 0.8720 | 820 | ever: 143/164 = 0.8720; final: 138/164 = 0.8415 | 820 | ever: +5 (+3.05 pp); final: +5 (+3.05 pp) |
| MBPP-427 | Single-pass | 307/427 = 0.7190 | 427 | 311/427 = 0.7283 | 427 | -4 (-0.94 pp) |
| MBPP-427 | Best-of-5 | 337/427 = 0.7892 | 2,135 | 343/427 = 0.8033 | 2,135 | -6 (-1.41 pp) |
| MBPP-427 | Adaptive hybrid refinement | 352/427 = 0.8244 | 647 | 351/427 = 0.8220 | 637 | +1 (+0.23 pp); +10 calls |
| MBPP-427 | Fixed-k=5 hybrid refinement | ever: 352/427 = 0.8244; final: 334/427 = 0.7822 | 2,135 | ever: 350/427 = 0.8197; final: 337/427 = 0.7892 | 2,135 | ever: +2 (+0.47 pp); final: -3 (-0.70 pp) |

For single-pass, best-of-5, and adaptive refinement, accuracy is the project's
problem-level headline metric: a problem is solved if the permitted generation
budget produces a passing candidate. Fixed-k reports that same ever-solved
metric first and the iteration-5-only diagnostic second. Calls are persisted
model generations, not estimates.

## Headline Tier 1 comparisons

On HumanEval, full-precision adaptive refinement solved 148/164 (`0.9024`),
four fewer than best-of-5's 152/164 (`0.9268`), while using 199 rather than
820 calls. Refinement therefore trailed by 2.44 percentage points but used
75.73% fewer calls.

On MBPP, full-precision adaptive refinement solved 352/427 (`0.8244`), 15
more than best-of-5's 337/427 (`0.7892`), while using 647 rather than 2,135
calls. Refinement therefore led by 3.51 percentage points and used 69.70%
fewer calls. This is the central positive Tier 1 result: on MBPP, iterative
execution feedback was both more accurate and substantially more
call-efficient than five independent samples.

Fixed-k produced no ever-solved gain over adaptive stopping on either
benchmark. It matched adaptive exactly at 148/164 on HumanEval and 352/427 on
MBPP, while forcing 820 and 2,135 calls respectively. Final-only evaluation
exposed five HumanEval and 18 MBPP success regressions, reducing the final
scores to 143/164 and 334/427. These results support success-priority adaptive
stopping and show that post-success generation is not monotonic refinement.

## Precision/backend comparison

Full precision exceeded Q4_K_M on all four HumanEval configurations under the
headline metric (+6 single-pass, +2 best-of-5, +5 adaptive, and +5 fixed-ever).
MBPP was mixed: full precision lost 4 single-pass and 6 best-of-5 solves, then
gained 1 adaptive and 2 fixed-ever solves. Adaptive refinement had the
smallest absolute net configuration change on MBPP (+1), consistent with
apparent relative robustness in aggregate, although paired task outcomes still
changed and the comparison is not causal.

Every Q4_K_M comparison is confounded by inference backend and hardware:
local runs used Ollama/CPU Q4_K_M, whereas reporting runs used Hugging
Face/CUDA `bfloat16`. The table reports observed end-to-end configuration
differences, not isolated effects of numerical precision. Matched seeds are
reproducibility metadata and do not imply token-identical sampling across
backends.

## Authoritative artifacts

| Benchmark | Configuration | Full-precision artifact | Q4_K_M artifact |
|---|---|---|---|
| HumanEval | Single-pass | [`20260808...zero_shot_humaneval_full`](../../experiments/results/20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full/) | [`20260715...single_humaneval_full`](../../experiments/results/20260715T215247Z_m7_quantized_local_development_single_humaneval_full/) |
| HumanEval | Best-of-5 | [`20260808...best_of_5_humaneval_full`](../../experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/) | [`20260716...best_of_5_humaneval_full`](../../experiments/results/20260716T225945.085688Z_m7_quantized_local_development_best_of_5_humaneval_full/) |
| HumanEval | Adaptive refinement | [`20260808...adaptive_humaneval_full`](../../experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/) | [`20260723...adaptive_humaneval_full`](../../experiments/results/20260723T191407.382508Z_m7_quantized_local_development_hybrid_refinement_adaptive_humaneval_full/) |
| HumanEval | Fixed-k refinement | [`20260808...fixed_humaneval_full`](../../experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/) | [`20260724...fixed_humaneval_full`](../../experiments/results/20260724T151654.164295Z_m7_quantized_local_development_hybrid_refinement_fixed_humaneval_full/) |
| MBPP | Single-pass | [`20260809...zero_shot_mbpp_full`](../../experiments/results/20260809T100420.122030Z_cluster_qwen_hf_zero_shot_mbpp_full/) | [`20260716...single_mbpp_full`](../../experiments/results/20260716T171911.599683Z_m7_quantized_local_development_single_mbpp_full/) |
| MBPP | Best-of-5 | [`20260809...best_of_5_mbpp_full`](../../experiments/results/20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full/) | [`20260720...best_of_5_mbpp_full`](../../experiments/results/20260720T101416.409257Z_m7_quantized_local_development_best_of_5_mbpp_full/) |
| MBPP | Adaptive refinement | [`20260809...adaptive_mbpp_full`](../../experiments/results/20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full/) | [`20260720...adaptive_mbpp_full`](../../experiments/results/20260720T112112.959147Z_m7_quantized_local_development_hybrid_refinement_adaptive_mbpp_full/) |
| MBPP | Fixed-k refinement | [`20260809...fixed_mbpp_full`](../../experiments/results/20260809T162731.848774Z_cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full/) | [`20260721...fixed_mbpp_full`](../../experiments/results/20260721T102049.383499Z_m7_quantized_local_development_hybrid_refinement_fixed_mbpp_full/) |

The corrected July 23 and July 24 HumanEval refinement artifacts are
authoritative; their earlier July 20 counterparts are superseded by the
compound-harness feedback correction. The corrected July 16 17:19 MBPP
single-pass artifact is authoritative; the earlier 16:33 run is superseded by
the stale-prompt correction.
