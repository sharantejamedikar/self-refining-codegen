# HumanEval-164 best-of-5 full-precision result

## Result

The full-precision (`bfloat16`) Qwen2.5-Coder-7B-Instruct run solved 152 of
164 HumanEval problems:

- `pass@1_bo5 = 152/164 = 0.9268`
- wall-clock: `1964.9322` seconds (32 minutes 44.93 seconds)
- prompt tokens: `147,785`
- completion tokens: `63,555`
- total tokens: `211,340`
- candidates: `820` (five per problem)

The committed Mac Q4_K_M comparison run solved 150 of 164
(`pass@1_bo5 = 0.9146`). The full-precision reporting configuration therefore
has an observed net advantage of two problems, or 1.22 percentage points
(1.2195 points before rounding).

As in the single-pass comparison, this is an **end-to-end configuration gap,
not a clean causal estimate of quantization alone**. Precision, inference
backend, and hardware changed together (Ollama/CPU Q4_K_M versus Hugging
Face/CUDA `bfloat16`). The random seeds are matched reproducibility metadata,
but different inference implementations do not guarantee token-for-token
sampling equivalence. The comparison supports using the full-precision result
for dissertation capability claims and treating the Mac result as a local
development baseline.

## Protocol and artifacts

Both runs used the pinned model revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, all 164 HumanEval tasks, zero-shot
prompts, five samples per problem, candidate seeds 42 through 46, temperature
0.8, top-p 0.95, maximum 512 new tokens, repetition penalty 1.1, and the
subprocess executor with a 10-second timeout and 512 MiB memory limit.

- Q4_K_M: [`20260716T225945.085688Z_m7_quantized_local_development_best_of_5_humaneval_full`](../../experiments/results/20260716T225945.085688Z_m7_quantized_local_development_best_of_5_humaneval_full/)
- Full precision: [`20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full`](../../experiments/results/20260808T210242.687568Z_cluster_qwen_hf_best_of_5_humaneval_full/)

Both artifact directories contain exactly 164 matching task IDs. The
full-precision run records all 820 candidates, its config snapshot, git commit,
seed derivation, per-problem JSON, summary CSV, and run summary.

## Outcome flips

| Problem | Q4_K_M | Full precision | Direction |
|---|---:|---:|---|
| HumanEval/10 | Fail | Pass | Recovered |
| HumanEval/95 | Fail | Pass | Recovered |
| HumanEval/125 | Fail | Pass | Recovered |
| HumanEval/130 | Fail | Pass | Recovered |
| HumanEval/115 | Pass | Fail | Lost |
| HumanEval/129 | Pass | Fail | Lost |

The four recoveries and two losses yield the observed net change of +2. The ten
tasks that failed in both configurations were HumanEval/26, /32, /38, /50,
/65, /83, /127, /132, /145, and /163.
