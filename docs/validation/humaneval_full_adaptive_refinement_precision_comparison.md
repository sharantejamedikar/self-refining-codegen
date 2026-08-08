# HumanEval-164 adaptive-refinement full-precision result

## Result

The full-precision (`bfloat16`) Qwen2.5-Coder-7B-Instruct adaptive hybrid
refinement run solved 148 of 164 HumanEval problems:

- `pass@1_refined = 148/164 = 0.9024`
- generation calls: `199`
- wall-clock: `491.5964` seconds (8 minutes 11.60 seconds)
- prompt tokens: `43,367`
- completion tokens: `16,028`
- total tokens: `59,395`

The run stopped with success for 148 tasks, oscillation for 9, and stagnation
for 7. Of the successful tasks, 141 succeeded on iteration 1, 6 on iteration
2, and 1 on iteration 3.

## Central compute-matched comparison

This session's full-precision best-of-5 run solved 152 of 164
(`pass@1_bo5 = 0.9268`) using 820 generation calls. Adaptive refinement
therefore **trails best-of-5 by 4 problems, or 2.44 percentage points**, while
using 199/820 = **24.27% of its generation calls** (4.12x fewer calls).

Using calls as the primary compute-cost measure requested for the headline
comparison, refinement does not match or exceed best-of-5 accuracy. Relative
to this session's full-precision single-pass result (142/164) and best-of-5
result (152/164), refinement recovers 6 of the 10 additional solves, closing
60% of the observed single-pass-to-best-of-5 accuracy gap.

For secondary resource measures, refinement used 59,395/211,340 = 28.10% of
best-of-5's total tokens and 491.5964/1964.9322 = 25.02% of its wall-clock.
The best-of-5 run used 147,785 prompt tokens, 63,555 completion tokens, and
211,340 total tokens.

Paired outcomes against full-precision best-of-5 were:

| Problem | Best-of-5 | Adaptive refinement | Direction |
|---|---:|---:|---|
| HumanEval/38 | Fail | Pass | Recovered |
| HumanEval/50 | Fail | Pass | Recovered |
| HumanEval/83 | Fail | Pass | Recovered |
| HumanEval/10 | Pass | Fail | Lost |
| HumanEval/64 | Pass | Fail | Lost |
| HumanEval/75 | Pass | Fail | Lost |
| HumanEval/95 | Pass | Fail | Lost |
| HumanEval/130 | Pass | Fail | Lost |
| HumanEval/141 | Pass | Fail | Lost |
| HumanEval/155 | Pass | Fail | Lost |

The nine tasks failed by both configurations were HumanEval/26, /32, /65,
/115, /127, /129, /132, /145, and /163.

## Q4_K_M comparison

The corrected Mac Q4_K_M adaptive run solved 143 of 164
(`pass@1_refined = 0.8720`) using 202 generation calls. The full-precision
reporting configuration therefore has an observed net advantage of five
problems, or 3.05 percentage points, and used three fewer calls.

This is an **end-to-end configuration gap, not a clean causal estimate of
quantization alone**. Precision, inference backend, and hardware changed
together (Ollama/CPU Q4_K_M versus Hugging Face/CUDA `bfloat16`). The random
seeds are matched reproducibility metadata, but different inference
implementations do not guarantee token-for-token sampling equivalence.

Paired outcome flips against the corrected Q4_K_M run were:

| Problem | Q4_K_M | Full precision | Direction |
|---|---:|---:|---|
| HumanEval/46 | Fail | Pass | Recovered |
| HumanEval/93 | Fail | Pass | Recovered |
| HumanEval/99 | Fail | Pass | Recovered |
| HumanEval/113 | Fail | Pass | Recovered |
| HumanEval/125 | Fail | Pass | Recovered |
| HumanEval/135 | Fail | Pass | Recovered |
| HumanEval/146 | Fail | Pass | Recovered |
| HumanEval/141 | Pass | Fail | Lost |
| HumanEval/155 | Pass | Fail | Lost |

The fourteen tasks failed by both configurations were HumanEval/10, /26, /32,
/64, /65, /75, /95, /115, /127, /129, /130, /132, /145, and /163.

## Protocol and artifacts

The run used pinned revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, all 164 frozen HumanEval tasks,
zero-shot prompts, seed 42, temperature 0.2, top-p 0.95, a maximum of 512 new
tokens, repetition penalty 1.1, hybrid feedback, at most five iterations,
stagnation patience 2, oscillation window 3, and the subprocess executor with
a 10-second timeout and 512 MiB memory limit.

- Corrected Q4_K_M adaptive refinement: [`20260723T191407.382508Z_m7_quantized_local_development_hybrid_refinement_adaptive_humaneval_full`](../../experiments/results/20260723T191407.382508Z_m7_quantized_local_development_hybrid_refinement_adaptive_humaneval_full/)
- Full-precision adaptive refinement: [`20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full`](../../experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/)
- Full-precision best-of-5: [`20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full`](../../experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/)

All three artifact directories contain exactly 164 matching task IDs. The new
run records all 199 generations, its config snapshot, git commit, seeds,
per-problem JSON, summary CSV, and run summary.
