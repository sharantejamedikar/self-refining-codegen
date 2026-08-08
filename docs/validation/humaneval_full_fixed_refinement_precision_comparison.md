# HumanEval-164 fixed-k=5 full-precision result

## Result

The full-precision (`bfloat16`) Qwen2.5-Coder-7B-Instruct hybrid refinement
run forced all 164 HumanEval problems through exactly five iterations:

- ever-solved `pass@1_refined_fixed = 148/164 = 0.9024`;
- final-iteration-only `pass@1_refined_fixed_final = 143/164 = 0.8720`;
- generation calls: `820` (`164 * 5`);
- wall-clock: `1,961.5902` seconds (32 minutes 41.59 seconds);
- prompt tokens: `213,113`;
- completion tokens: `63,034`;
- total tokens: `276,147`.

All 164 persisted problem records contain exactly five iterations. The
ever-solved metric counts a problem if any of those iterations passed; the
final-only diagnostic counts only iteration 5.

## Adaptive-stopping comparison

The matching full-precision adaptive run solved 148/164 (`0.9024`) using 199
calls. Fixed-k therefore produced no ever-solved gains or losses relative to
adaptive stopping, while requiring 621 additional calls: 820/199 = 4.12 times
as many calls.

Forced iteration was **neutral under the protocol's ever-solved metric** but
**harmful under final-only evaluation**. Five tasks that passed earlier in the
fixed trajectory failed at iteration 5:

- HumanEval/74;
- HumanEval/81;
- HumanEval/109;
- HumanEval/126;
- HumanEval/160.

Thus final-only accuracy was five problems (3.05 percentage points) below the
adaptive result. Forced continuation recovered none of the 16 adaptive
failures. HumanEval/75 remained a logic failure in all five iterations.

## Authoritative Q4_K_M comparison

The authoritative corrected Mac Q4_K_M fixed-k=5 run solved 143/164 ever
(`0.8720`) and 138/164 at iteration 5 (`0.8415`), using 820 calls. At matched
call count, full precision therefore exceeded Q4_K_M by five problems, or
**3.05 percentage points**, under both definitions:

| Precision/backend | Ever solved | Final-only | Calls |
|---|---:|---:|---:|
| Q4_K_M / Ollama | 143/164 = 0.8720 | 138/164 = 0.8415 | 820 |
| `bfloat16` / Hugging Face | 148/164 = 0.9024 | 143/164 = 0.8720 | 820 |
| Difference | +5/164 = +3.05 pp | +5/164 = +3.05 pp | 0 |

For ever-solved outcomes, full precision recovered HumanEval/46, /93, /99,
/113, /125, /135, and /146 relative to Q4_K_M, while losing HumanEval/141
and /155. This yields the net five-problem advantage. The observed difference
is an end-to-end configuration gap, not a clean causal estimate of
quantization alone: inference backend and hardware also differ.

The success-regression phenomenon occurred at both precisions. Full precision
had five ever-solved tasks fail at iteration 5; corrected Q4_K_M also had five
(HumanEval/81, /100, /134, /138, and /160).

### Q4_K_M provenance warning

Use the **July 24 corrected artifact**
[`20260724T151654.164295Z_m7_quantized_local_development_hybrid_refinement_fixed_humaneval_full`](../../experiments/results/20260724T151654.164295Z_m7_quantized_local_development_hybrid_refinement_fixed_humaneval_full/)
for every future comparison and dissertation table. Its authoritative figures
are 143 ever-solved and 138 final-only.

The July 20 artifact reports 144 ever-solved and 140 final-only, but it is
superseded because its refinement feedback could cite the wrong assertion from
a compound HumanEval harness. The July 24 run was produced after the
traceback-based feedback correction and passed the feedback-fidelity audit.
The defect, rerun validation, supersession decision, and authoritative figures
are documented in
[`m7_humaneval_feedback_correction.md`](m7_humaneval_feedback_correction.md).
The July 20 artifact remains only as provenance for the confounded run and
must not be used for reported comparisons.

## Protocol and artifacts

The full-precision run used pinned model revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, the frozen 164-problem HumanEval
set, seed 42, temperature 0.2, top-p 0.95, at most 512 new tokens per call,
repetition penalty 1.1, hybrid feedback, and the subprocess executor with a
10-second timeout and 512 MiB memory limit. Fixed mode disabled success,
stagnation, and oscillation stopping until iteration 5.

- Full-precision fixed-k=5:
  [`20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full`](../../experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/)
- Full-precision adaptive:
  [`20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full`](../../experiments/results/20260808T215208.948344Z_cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_full/)
- Authoritative corrected Q4_K_M fixed-k=5:
  [`20260724T151654.164295Z_m7_quantized_local_development_hybrid_refinement_fixed_humaneval_full`](../../experiments/results/20260724T151654.164295Z_m7_quantized_local_development_hybrid_refinement_fixed_humaneval_full/)
