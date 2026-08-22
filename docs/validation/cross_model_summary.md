# Cross-model summary

## Scope and comparability

This table compares the four completed HumanEval-164 configurations for
`Qwen/Qwen2.5-Coder-7B-Instruct` and
`codellama/CodeLlama-13b-Instruct-hf`. Qwen was run in non-quantised
`bfloat16` with the Hugging Face CUDA backend; CodeLlama was run with bitsandbytes 8-bit
quantization. This is therefore **not a clean, precision-controlled model
comparison**. Model family, model size, numerical precision, and the associated
inference configuration differ. The results support cross-configuration
replication of qualitative patterns, but they do not isolate a causal model or
precision effect.

The CodeLlama single-pass, best-of-5, and adaptive-refinement configurations
have now also been run on sanitized MBPP-427. The MBPP
comparison below remains descriptive: benchmark difficulty and task contracts
differ from HumanEval, while the Qwen comparisons additionally confound model
family, parameter count, numerical precision, and (for Q4_K_M) inference
backend.

## Master results

| Configuration | Qwen non-quantised `bfloat16` accuracy | Qwen calls | CodeLlama 8-bit accuracy | CodeLlama calls | Gap closure |
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
was quantized while Qwen used non-quantised `bfloat16`.

Forced-iteration regression is confirmed across both model families. In the
fixed-k runs, 9 CodeLlama problems that passed at an earlier iteration failed
at iteration 5, compared with 5 Qwen problems. Expressed using the requested
fixed-run reporting denominators, these are 9/87 (10.3%) for CodeLlama and
5/148 (3.4%) for Qwen. The underlying ever-solved-to-final changes are 87 to
78 and 148 to 143, respectively. This replication supports the
model-agnostic existence of the regression phenomenon and the use of
success-priority adaptive stopping. It does **not** establish that CodeLlama
has a higher intrinsic regression rate: the comparison has only one run per
configuration and is confounded by model family, model size, and precision
(8-bit CodeLlama versus non-quantised `bfloat16` Qwen).

## MBPP-427 extension

| Model configuration | Method | Solved | pass@1 | Calls | Wall clock | Total tokens |
|---|---|---:|---:|---:|---:|---:|
| CodeLlama-13B, bitsandbytes 8-bit | Single-pass | 192/427 | 0.4496 | 427 | 3,389.17 s | 67,427 |
| CodeLlama-13B, bitsandbytes 8-bit | Best-of-5 | **263/427** | **0.6159** | 2,135 | 18,310.02 s | 348,041 |
| CodeLlama-13B, bitsandbytes 8-bit | Adaptive hybrid refinement | 257/427 | 0.6019 | **821** | **8,039.95 s** | **309,044** |
| CodeLlama-13B, bitsandbytes 8-bit | Fixed-k=5 hybrid refinement (ever solved) | 257/427 | 0.6019 | 2,135 | 18,916.06 s | 777,571 |
| CodeLlama-13B, bitsandbytes 8-bit | Fixed-k=5 final iteration only | 211/427 | 0.4941 | 2,135 | 18,916.06 s | 777,571 |
| Qwen-7B, Hugging Face `bfloat16` | Adaptive hybrid refinement | 352/427 | 0.8244 | 647 | 1,505.82 s | 206,160 |
| Qwen-7B, Ollama Q4_K_M | Adaptive hybrid refinement | 351/427 | 0.8220 | 637 | 1,450.89 s | 197,079 |

CodeLlama adaptive refinement improved over its own single-pass result by 65
solves (+15.22 percentage points), using 821 calls rather than 427. It did
**not** reproduce Qwen's MBPP pattern of refinement beating best-of-5:
CodeLlama refinement finished 6 solves below best-of-5 (-1.41 percentage
points). The paired comparison contained 29 refinement-only passes and 35
best-of-5-only passes (exact two-sided McNemar `p=0.5323`; matched odds ratio
`0.8286`). Thus the observed six-problem deficit is not statistically
significant at 0.05. Refinement nevertheless used 1,314 fewer calls (61.55%
fewer), 10,270.06 fewer summed wall-clock seconds (56.09% fewer), and 38,997
fewer tokens (11.20% fewer) than best-of-5. Its seed-42, 10,000-resample
bootstrap 95% CI was `[0.5550, 0.6487]`.

The Qwen contrast is qualitative and clear: non-quantised `bfloat16` Qwen adaptive
refinement solved 352/427, 15 more than its own best-of-5, while Q4_K_M Qwen
adaptive refinement solved 351/427, 8 more than its own best-of-5. CodeLlama
adaptive refinement instead solved 257/427, 6 fewer than its own best-of-5.
Accordingly, the claim that adaptive refinement beats best-of-5 on MBPP is
supported for both tested Qwen precision configurations but does not
generalize to this CodeLlama-13B 8-bit configuration.

Fixed iteration produced no ever-solved gain over adaptive CodeLlama: both
solved exactly the same 257 tasks. It nevertheless used 2,135 versus 821 calls
(2.60x; 1,314 extra), 777,571 versus 309,044 tokens (2.52x), and 18,916.06
versus 8,039.95 summed wall-clock seconds (2.35x). At iteration 5 only 211
tasks still passed, so 46/257 (17.9%) ever-solved tasks regressed. All 46 next
prompts paired `All assertions passed.` with `Return a corrected complete
solution.`, replicating the same self-contradictory post-success instruction
in the other five fixed-run conditions. This sixth condition completes the
executed two-model, two-benchmark fixed-run coverage, with Qwen represented at
both non-quantised `bfloat16` and Q4_K_M.

On CodeLlama, MBPP single-pass exceeded its own HumanEval single-pass result by
3.50 percentage points (44.96% versus 41.46%). This is not evidence that MBPP
is intrinsically easier: the benchmarks differ in tasks, tests, prompts, and
denominators.

On the shared MBPP-427 task set, CodeLlama solved 115 fewer problems than
non-quantised `bfloat16` Qwen (a 26.93 percentage-point deficit) and 119 fewer than
Q4_K_M Qwen (a 27.87 percentage-point deficit). These are end-to-end
configuration differences, not isolated model-family effects. CodeLlama has
13B parameters and used bitsandbytes 8-bit through Hugging Face; the Qwen
configuration has 7B parameters and used either Hugging Face `bfloat16` or
Ollama Q4_K_M. Quantization format, numerical precision, model family, model
size, and—in the Q4_K_M comparison—inference backend are all confounded. Each
configuration is represented by one fixed-seed run, so run-to-run variability
is also unmeasured.

## Authoritative artifacts

| Configuration | Qwen non-quantised `bfloat16` | CodeLlama 8-bit |
|---|---|---|
| Single-pass | [`20260808...zero_shot`](../../experiments/results/20260808T204450.467851Z_cluster_qwen_hf_zero_shot_humaneval_full/) | [`20260810...zero_shot`](../../experiments/results/20260810T113106.471817Z_cluster_codellama_13b_bnb_8bit_zero_shot_humaneval_full/) |
| Best-of-5 | [`20260808...best_of_5`](../../experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/) | [`20260810...best_of_5`](../../experiments/results/20260810T121044.505386Z_cluster_codellama_13b_bnb_8bit_best_of_5_humaneval_full/) |
| Adaptive refinement | [`20260808...adaptive`](../../experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/) | [`20260810...adaptive`](../../experiments/results/20260810T164232.226049Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_humaneval_full/) |
| Fixed-k refinement | [`20260808...fixed`](../../experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/) | [`20260810...fixed`](../../experiments/results/20260810T220239.789427Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_humaneval_full/) |

The authoritative CodeLlama MBPP artifacts are
[`20260811...zero_shot_mbpp`](../../experiments/results/20260811T125007.528701Z_cluster_codellama_13b_bnb_8bit_zero_shot_mbpp_full/),
[`20260811...best_of_5_mbpp`](../../experiments/results/20260811T185140.732397Z_cluster_codellama_13b_bnb_8bit_best_of_5_mbpp_full/), and
[`20260812...adaptive_mbpp`](../../experiments/results/20260812T222900Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_adaptive_mbpp_full/), and
[`20260813...fixed_mbpp`](../../experiments/results/20260813T005000Z_cluster_codellama_13b_bnb_8bit_hybrid_refinement_fixed_mbpp_full/).
The fixed-run case audit is
[`codellama_mbpp_fixed_refinement_analysis.md`](codellama_mbpp_fixed_refinement_analysis.md).
The complete standard-benchmark paired statistics, including aligned task IDs,
effect sizes and exact McNemar results, are frozen in
[`standard_benchmark_statistics.json`](standard_benchmark_statistics.json).
Their persisted commits are `b24f31bc468c81706844aa4f01c4c376c15a9e37`,
`20b161898692443e3aa32b5c83338841beb4753b`, and
`20b161898692443e3aa32b5c83338841beb4753b`; the fixed artifact's commit is
`80bde190b03b441b7e2328b8b8475cd8353c440f`.
