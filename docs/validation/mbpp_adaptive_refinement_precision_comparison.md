# Qwen2.5-Coder-7B adaptive-refinement precision comparison on MBPP-427

## Result

The full-precision (`bfloat16`) Qwen2.5-Coder-7B-Instruct adaptive hybrid
refinement run solved 352 of 427 sanitized MBPP problems:

- `pass@1_refined = 352/427 = 0.8244`;
- generation calls: `647`;
- wall-clock: `1,505.8236` seconds (25 minutes 5.82 seconds);
- prompt tokens: `167,208`;
- completion tokens: `38,952`;
- total tokens: `206,160`.

The run stopped with success for 352 tasks, oscillation for 46, stagnation
for 18, and the five-iteration maximum for 11. Of the successful tasks, 307
succeeded on iteration 1, 36 on iteration 2, 6 on iteration 3, and 3 on
iteration 4.

## Methodology and controls

The three paired artifacts were:

- Q4_K_M adaptive refinement: [`20260720T112112.959147Z_m7_quantized_local_development_hybrid_refinement_adaptive_mbpp_full`](../../experiments/results/20260720T112112.959147Z_m7_quantized_local_development_hybrid_refinement_adaptive_mbpp_full/)
- Full-precision adaptive refinement: [`20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full`](../../experiments/results/20260809T155124.955006Z_cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full/)
- Full-precision best-of-5: [`20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full`](../../experiments/results/20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full/)

All three directories contain exactly the same 427 task IDs from the frozen
sanitized MBPP set. They use canonical model
`Qwen/Qwen2.5-Coder-7B-Instruct`, pinned Hugging Face revision
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, the zero-shot prompt contract,
top-p 0.95, a maximum of 512 new tokens, repetition penalty 1.1, and the
subprocess executor with a 10-second timeout and 512 MiB memory limit.

Adaptive refinement used seed 42, temperature 0.2, hybrid feedback, at most
five iterations, stagnation patience 2, and oscillation window 3. Best-of-5
used five independent candidate seeds 42--46 and temperature 0.8. The local
adaptive run used Ollama `qwen2.5-coder:7b-instruct-q4_K_M`; the cluster runs
loaded the pinned model revision through Hugging Face as `torch.bfloat16`
without quantization.

## Q4_K_M adaptive-refinement comparison

The Q4_K_M adaptive run solved 351/427 (`0.8220`) using 637 calls. Full
precision therefore gained one problem, or **0.23 percentage points**, while
using ten more calls. There were 25 paired outcome flips: 13 recoveries and
12 losses.

| Problem | Q4_K_M adaptive | Full-precision adaptive | Direction |
|---|---:|---:|---|
| MBPP/67 | Fail | Pass | Recovered |
| MBPP/72 | Pass | Fail | Lost |
| MBPP/87 | Fail | Pass | Recovered |
| MBPP/103 | Fail | Pass | Recovered |
| MBPP/143 | Pass | Fail | Lost |
| MBPP/167 | Pass | Fail | Lost |
| MBPP/229 | Pass | Fail | Lost |
| MBPP/245 | Fail | Pass | Recovered |
| MBPP/252 | Fail | Pass | Recovered |
| MBPP/259 | Fail | Pass | Recovered |
| MBPP/290 | Fail | Pass | Recovered |
| MBPP/308 | Pass | Fail | Lost |
| MBPP/424 | Fail | Pass | Recovered |
| MBPP/429 | Fail | Pass | Recovered |
| MBPP/581 | Pass | Fail | Lost |
| MBPP/592 | Fail | Pass | Recovered |
| MBPP/596 | Fail | Pass | Recovered |
| MBPP/643 | Pass | Fail | Lost |
| MBPP/644 | Fail | Pass | Recovered |
| MBPP/721 | Pass | Fail | Lost |
| MBPP/735 | Pass | Fail | Lost |
| MBPP/742 | Pass | Fail | Lost |
| MBPP/773 | Fail | Pass | Recovered |
| MBPP/788 | Pass | Fail | Lost |
| MBPP/808 | Pass | Fail | Lost |

The paired contingency counts are 339 pass/pass, 12 Q4_K_M-only passes, 13
full-precision-only passes, and 63 fail/fail.

This is an **end-to-end configuration comparison, not a clean causal estimate
of quantization alone**. Precision, inference backend, and hardware changed
together (Ollama/CPU Q4_K_M versus Hugging Face/CUDA `bfloat16`). Matched seed
metadata does not guarantee token-identical sampling across inference
implementations.

Even with that limitation, adaptive refinement is apparently less sensitive
in aggregate to this precision/backend confound than the two MBPP single-shot
methods. Full precision changed single-pass from 311 to 307 solved (-4) and
best-of-5 from 343 to 337 (-6), whereas adaptive refinement changed from 351
to 352 (+1). The adaptive result is nearly identical across configurations
despite 25 task-level flips. This supports a cautious **relative robustness**
observation, not a causal claim that refinement neutralizes quantization: the
comparison covers only one benchmark, seed, model family, and paired backend
configuration.

## Full-precision best-of-5 comparison

The full-precision best-of-5 run solved 337/427
(`pass@1_bo5 = 0.7892`) using 2,135 generation calls. Adaptive refinement
therefore **solved 15 more problems, or 3.51 percentage points**, confirming
that the central “refinement beats best-of-5 on MBPP” finding replicates in
the reporting full-precision configuration.

| Problem | Full-precision best-of-5 | Full-precision adaptive | Direction |
|---|---:|---:|---|
| MBPP/9 | Fail | Pass | Recovered |
| MBPP/63 | Pass | Fail | Lost |
| MBPP/72 | Pass | Fail | Lost |
| MBPP/87 | Fail | Pass | Recovered |
| MBPP/91 | Fail | Pass | Recovered |
| MBPP/115 | Pass | Fail | Lost |
| MBPP/123 | Pass | Fail | Lost |
| MBPP/164 | Pass | Fail | Lost |
| MBPP/167 | Pass | Fail | Lost |
| MBPP/229 | Pass | Fail | Lost |
| MBPP/249 | Fail | Pass | Recovered |
| MBPP/252 | Fail | Pass | Recovered |
| MBPP/259 | Fail | Pass | Recovered |
| MBPP/279 | Fail | Pass | Recovered |
| MBPP/290 | Fail | Pass | Recovered |
| MBPP/294 | Fail | Pass | Recovered |
| MBPP/308 | Pass | Fail | Lost |
| MBPP/391 | Fail | Pass | Recovered |
| MBPP/393 | Fail | Pass | Recovered |
| MBPP/396 | Fail | Pass | Recovered |
| MBPP/400 | Fail | Pass | Recovered |
| MBPP/407 | Fail | Pass | Recovered |
| MBPP/421 | Fail | Pass | Recovered |
| MBPP/427 | Fail | Pass | Recovered |
| MBPP/428 | Pass | Fail | Lost |
| MBPP/429 | Fail | Pass | Recovered |
| MBPP/437 | Fail | Pass | Recovered |
| MBPP/440 | Fail | Pass | Recovered |
| MBPP/442 | Fail | Pass | Recovered |
| MBPP/446 | Fail | Pass | Recovered |
| MBPP/475 | Fail | Pass | Recovered |
| MBPP/477 | Fail | Pass | Recovered |
| MBPP/592 | Fail | Pass | Recovered |
| MBPP/595 | Fail | Pass | Recovered |
| MBPP/596 | Fail | Pass | Recovered |
| MBPP/597 | Pass | Fail | Lost |
| MBPP/610 | Pass | Fail | Lost |
| MBPP/624 | Fail | Pass | Recovered |
| MBPP/631 | Fail | Pass | Recovered |
| MBPP/643 | Pass | Fail | Lost |
| MBPP/721 | Pass | Fail | Lost |
| MBPP/722 | Fail | Pass | Recovered |
| MBPP/735 | Pass | Fail | Lost |
| MBPP/750 | Fail | Pass | Recovered |
| MBPP/753 | Fail | Pass | Recovered |
| MBPP/755 | Pass | Fail | Lost |
| MBPP/773 | Fail | Pass | Recovered |
| MBPP/776 | Fail | Pass | Recovered |
| MBPP/788 | Pass | Fail | Lost |
| MBPP/804 | Pass | Fail | Lost |
| MBPP/808 | Pass | Fail | Lost |

The paired contingency counts are 319 pass/pass, 18 best-of-5-only passes, 33
adaptive-only passes, and 57 fail/fail. The 33 recoveries and 18 losses yield
the net 15-problem advantage.

The accuracy improvement also accompanies a substantial efficiency advantage.
Adaptive refinement used 647 rather than 2,135 calls: **69.70% fewer calls**
(3.30x fewer). It used 206,160 rather than 281,253 total tokens: **26.68% of
the token budget, or 73.32% fewer tokens**. It used 1,505.8236 rather than
4,285.2543 wall-clock seconds: **35.14% of the time, or 64.86% less
wall-clock**. Rounded to whole percentages, refinement used 70% fewer calls,
73% fewer tokens, and 65% less wall-clock while solving 15 additional
problems.

## Interpretation

The full-precision run is the authoritative reported result and independently
preserves the core MBPP conclusion observed during Q4_K_M development:
adaptive execution-feedback refinement outperforms five independent samples
under the project's problem-level metric. The result is stronger than a
compute-parity claim because refinement is both more accurate and markedly
less expensive on all three recorded resource measures.

The near equality of Q4_K_M and full-precision adaptive accuracy is also
notable beside the larger net changes for MBPP single-pass and best-of-5.
Adaptive feedback may make aggregate outcomes more stable by giving later
calls concrete evidence about earlier failures, but this mechanism was not
isolated experimentally. The defensible dissertation wording is therefore
that refinement showed **apparent relative robustness to the observed
precision/backend configuration change**, while causal attribution requires a
controlled precision comparison holding backend and hardware fixed.

## Reproducibility note

The full-precision artifact records all 647 generations, its config snapshot,
git commit, seeds, per-problem JSON, summary CSV, and run summary. Before this
report was created, the repository test suite completed with 127 passing tests
in 6.06 seconds.
