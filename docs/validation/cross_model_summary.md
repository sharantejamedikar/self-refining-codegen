# Cross-model summary

## Scope and comparability

This table compares the four completed HumanEval-164 configurations for
`Qwen/Qwen2.5-Coder-7B-Instruct` and
`codellama/CodeLlama-13b-Instruct-hf`. Qwen was run in full precision with the
Hugging Face CUDA backend; CodeLlama was run with bitsandbytes 8-bit
quantization. This is therefore **not a clean, precision-controlled model
comparison**. Model family, model size, numerical precision, and the associated
inference configuration differ. The results support cross-configuration
replication of qualitative patterns, but they do not isolate a causal model or
precision effect.

CodeLlama single-pass has now also been run on sanitized MBPP-427. The MBPP
comparison below remains descriptive: benchmark difficulty and task contracts
differ from HumanEval, while the Qwen comparisons additionally confound model
family, parameter count, numerical precision, and (for Q4_K_M) inference
backend.

## Master results

| Configuration | Qwen full-precision accuracy | Qwen calls | CodeLlama 8-bit accuracy | CodeLlama calls | Gap closure |
|---|---:|---:|---:|---:|---:|
| Single-pass | 142/164 = 86.59% | 164 | 68/164 = 41.46% | 164 | — |
| Best-of-5 | 152/164 = 92.68% | 820 | 102/164 = 62.20% | 820 | Reference |
| Adaptive hybrid refinement | 148/164 = 90.24% | 199 | 87/164 = 53.05% | 311 | Qwen: 60.0%; CodeLlama: 55.9% |
| Fixed-k=5 hybrid refinement | ever: 148/164 = 90.24%; final: 143/164 = 87.20% | 820 | ever: 87/164 = 53.05%; final: 78/164 = 47.56% | 820 | Qwen: 60.0%; CodeLlama: 55.9% (ever-solved) |

Calls are persisted model generations, not estimates. The refinement headline
metric is ever solved within at most five iterations. The fixed-k row also
reports iteration-5-only accuracy to expose outcomes that regress after an
earlier success.

Gap closure measures how much of the improvement from single-pass to
best-of-5 is recovered by refinement:

`(refinement solved - single-pass solved) / (best-of-5 solved - single-pass solved)`.

For Qwen this is `(148 - 142) / (152 - 142) = 6/10 = 60.0%`. For
CodeLlama it is `(87 - 68) / (102 - 68) = 19/34 = 55.9%`.

## Interpretation

The qualitative result generalizes across these two model configurations:
adaptive execution-feedback refinement improves substantially over
single-pass generation and approaches the best-of-5 result with fewer calls.
Qwen refinement recovered 60.0% of the best-of-5 improvement with 199 calls,
75.7% fewer than best-of-5. CodeLlama refinement recovered 55.9% with 311
calls, 62.1% fewer than best-of-5. Thus the evidence supports the pattern that
refinement can approach best-of-5 more efficiently across model families.

The quantitative result is weaker for the less capable CodeLlama
configuration. Its refinement result remains 15 solves (9.15 percentage
points) behind best-of-5, compared with Qwen's remaining deficit of 4 solves
(2.44 percentage points). Its gap closure is also lower, 55.9% versus 60.0%.
These are descriptive end-to-end configuration differences; the comparison
cannot attribute the difference solely to model capability because CodeLlama
was quantized while Qwen was full precision.

Forced-iteration regression is confirmed across both model families. In the
fixed-k runs, 9 CodeLlama problems that passed at an earlier iteration failed
at iteration 5, compared with 5 Qwen problems. Expressed using the requested
fixed-run reporting denominators, these are 9/87 (10.3%) for CodeLlama and
5/143 (3.5%) for Qwen. The underlying ever-solved-to-final changes are 87 to
78 and 148 to 143, respectively. This replication supports the
model-agnostic existence of the regression phenomenon and the use of
success-priority adaptive stopping. It does **not** establish that CodeLlama
has a higher intrinsic regression rate: the comparison has only one run per
configuration and is confounded by model family, model size, and precision
(8-bit CodeLlama versus full-precision Qwen).

## MBPP-427 single-pass extension

| Model configuration | Solved | `pass@1_single` | Wall clock | Prompt tokens | Completion tokens | Total tokens |
|---|---:|---:|---:|---:|---:|---:|
| CodeLlama-13B, bitsandbytes 8-bit | 192/427 | 0.4496 | 3,389.17 s (56m 29.17s) | 43,492 | 23,935 | 67,427 |
| Qwen-7B, Hugging Face `bfloat16` | 307/427 | 0.7190 | — | — | — | — |
| Qwen-7B, Ollama Q4_K_M | 311/427 | 0.7283 | — | — | — | — |

On CodeLlama, MBPP single-pass exceeded its own HumanEval single-pass result by
3.50 percentage points (44.96% versus 41.46%). This is not evidence that MBPP
is intrinsically easier: the benchmarks differ in tasks, tests, prompts, and
denominators.

On the shared MBPP-427 task set, CodeLlama solved 115 fewer problems than
full-precision Qwen (a 26.93 percentage-point deficit) and 119 fewer than
Q4_K_M Qwen (a 27.87 percentage-point deficit). These are end-to-end
configuration differences, not isolated model-family effects. CodeLlama has
13B parameters and used bitsandbytes 8-bit through Hugging Face; the Qwen
configuration has 7B parameters and used either Hugging Face `bfloat16` or
Ollama Q4_K_M. Quantization format, numerical precision, model family, model
size, and—in the Q4_K_M comparison—inference backend are all confounded. Each
configuration is represented by one fixed-seed run, so run-to-run variability
is also unmeasured.

## Authoritative artifacts

| Configuration | Qwen full precision | CodeLlama 8-bit |
|---|---|---|
| Single-pass | [`20260808...zero_shot`](../../experiments/results/20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full/) | [`20260810...zero_shot`](../../experiments/results/20260810T113106.471817Z_cluster_codellama_13b_bnb_8bit_zero_shot_humaneval_full/) |
| Best-of-5 | [`20260808...best_of_5`](../../experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/) | [`20260810...best_of_5`](../../experiments/results/20260810T121044.505386Z_cluster_codellama_13b_bnb_8bit_best_of_5_humaneval_full/) |
| Adaptive refinement | [`20260808...adaptive`](../../experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/) | [`20260810...adaptive`](../../experiments/results/20260810T164232.226049Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_full/) |
| Fixed-k refinement | [`20260808...fixed`](../../experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/) | [`20260810...fixed`](../../experiments/results/20260810T220239.789427Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_humaneval_full/) |

The authoritative CodeLlama MBPP single-pass artifact is
[`20260811...zero_shot_mbpp`](../../experiments/results/20260811T125007.528701Z_cluster_codellama_13b_bnb_8bit_zero_shot_mbpp_full/),
persisted at git commit `b24f31bc468c81706844aa4f01c4c376c15a9e37`.
