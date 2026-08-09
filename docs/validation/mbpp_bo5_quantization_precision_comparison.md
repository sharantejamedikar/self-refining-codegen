# Qwen2.5-Coder-7B best-of-5 precision comparison on MBPP-427

## Result

On the 427-task sanitized MBPP benchmark, the authoritative local Q4_K_M
best-of-5 run solved 343 problems (`pass@1_bo5 = 343/427 = 0.8033`) and the
full-precision (`bfloat16`) cluster run solved 337
(`337/427 = 0.7892`). Full precision therefore has an observed net deficit of
six problems, or **-1.41 percentage points** (-1.4052 points before rounding).
Sixteen problem outcomes changed: full precision recovered five Q4_K_M
failures and lost eleven Q4_K_M successes.

This is an **end-to-end configuration comparison, not a clean causal estimate
of quantization alone**. Precision, inference backend, and hardware changed
together (Ollama/CPU Q4_K_M versus Hugging Face/CUDA `bfloat16`). Matched
seeds are reproducibility metadata, but different inference implementations
do not guarantee token-identical sampling. The result supports reporting the
full-precision run as the dissertation result while retaining the Q4_K_M run
as a documented local-development baseline; it does not support applying a
post-hoc correction factor between them.

## Methodology and controls

The paired artifacts were:

- Q4_K_M: [`20260720T101416.409257Z_m7_quantized_local_development_best_of_5_mbpp_full`](../../experiments/results/20260720T101416.409257Z_m7_quantized_local_development_best_of_5_mbpp_full/)
- Full precision: [`20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full`](../../experiments/results/20260809T103719.229806Z_cluster_qwen_hf_best_of_5_mbpp_full/)

Both runs contain exactly the same 427 MBPP task IDs and use the sanitized
dataset, canonical model `Qwen/Qwen2.5-Coder-7B-Instruct`, pinned Hugging Face
revision `c03e6d358207e414f1eca0bb1891e29f1db0e242`, zero-shot prompt contract,
five candidates per problem, candidate seeds 42 through 46, temperature 0.8,
top-p 0.95, maximum 512 new tokens, repetition penalty 1.1, and the subprocess
executor with a 10-second timeout and 512 MiB memory limit. Each run records
2,135 candidates. The Q4_K_M artifact reports 1,313 unique code outputs and
2,931.0119 seconds wall-clock; the full-precision artifact reports 1,295
unique outputs, 4,285.2543 seconds wall-clock, 166,610 prompt tokens, and
114,643 completion tokens.

The local run used Ollama `qwen2.5-coder:7b-instruct-q4_K_M`; the cluster run
loaded the pinned Hugging Face revision as `torch.bfloat16` without
quantization. Candidate numbers below are one-based; candidate 1 corresponds
to seed 42 and candidate 5 to seed 46. `P` and `F` show each run's five
candidate outcomes in seed order.

## Outcome flips

| Problem | Q4_K_M candidates | Full-precision candidates | Direction | Candidate-level code explanation |
|---|---:|---:|---|---|
| MBPP/59 | `FFFFP` | `FFFFF` | Lost | Q4 candidate 5 returned the nth octagonal number, `n * (3*n - 2)`; all full-precision candidates instead tried to recognize whether the input was octagonal. |
| MBPP/115 | `FFFFF` | `FFFFP` | Recovered | Full-precision candidate 5 alone preserved the dataset's required (misspelled) function name `empty_dit`; every Q4 candidate defined `empty_dict`, causing `NameError`. |
| MBPP/167 | `FFFFF` | `PFFFF` | Recovered | Full-precision candidate 1 guarded `n <= 1` before `log2`; every Q4 candidate called `log2(0)` and raised `ValueError`. |
| MBPP/239 | `FFFFP` | `FFFFF` | Lost | Q4 candidate 5 used the tested recurrence `dp[i][j] = dp[i-1][j] + dp[i//2][j-1]`; the five full-precision candidates used incorrect bounds, states, or recurrences. |
| MBPP/279 | `FFPFP` | `FFFFF` | Lost | Q4 candidates 3 and 5 returned the required decagonal formula `4*n**2 - 3*n`; full precision produced recognition predicates or incorrect formulae. |
| MBPP/405 | `PFFFF` | `FFFFF` | Lost | Q4 candidate 1 correctly evaluated `tuple1 in tuplex`; full precision reversed the operands or referenced an undefined `item`. |
| MBPP/421 | `FFPFF` | `FFFFF` | Lost | Q4 candidate 3 joined stringified tuple elements with hyphens; full precision omitted separators, used the wrong delimiter, or returned a list. |
| MBPP/424 | `FFFFF` | `FPPPP` | Recovered | Full-precision candidates 2--5 returned a list of final characters; all Q4 candidates returned a tuple, contrary to the tests. |
| MBPP/429 | `FFFFP` | `FFFFF` | Lost | Q4 candidate 5 applied element-wise bitwise `&`; full precision used Boolean `and`, filtered equal pairs, or wrapped extra tuples. |
| MBPP/581 | `PPFPF` | `FFFFF` | Lost | Q4 candidates 1, 2, and 4 used the tested square-pyramid formula `b**2 + 2*b*s`; every full-precision candidate reinterpreted `s` and derived a different height. |
| MBPP/592 | `FFPFP` | `FFFFF` | Lost | Q4 candidates 3 and 5 summed `C(n,i-1)C(n,i)` through `i=n`; full precision omitted the endpoint or used the loop index as a binomial argument. |
| MBPP/596 | `FFFPF` | `FFFFF` | Lost | Q4 candidate 4 returned `sys.getsizeof(tuple_list)`; all full-precision candidates summed element sizes (and one also added the tuple size). |
| MBPP/610 | `FFFFF` | `FFFPF` | Recovered | Full-precision candidate 4 treated `L` as the tested one-based position (`[:L-1] + [L:]`); all Q4 candidates removed zero-based index `L`. |
| MBPP/624 | `FFFFP` | `FFFFF` | Lost | Q4 candidate 5 returned `string.upper()`; all full-precision candidates returned the Boolean result of an uppercase check. |
| MBPP/755 | `FFFFF` | `FPFFF` | Recovered | Full-precision candidate 2 required `first < num < second`, correctly ignoring duplicate minima; every Q4 candidate used `<=` and returned the repeated minimum. |
| MBPP/765 | `FFPFF` | `FFFFF` | Lost | Q4 candidate 3 enumerated non-powers-of-two and returned the nth polite number; full precision returned Boolean politeness tests or otherwise failed to enumerate the requested value. |

The five recoveries and eleven losses yield the observed net change of -6.
Candidate-level inspection found generated-code differences for every flip;
none is explained by a missing execution dependency. MBPP/596's expected
`sys.getsizeof` value differs across the local and cluster Python builds, but
the correct implementation is environment-relative and would pass on either
host; only the Q4_K_M pool sampled it.

## Paired significance test

The problem-level contingency table is:

| | Full precision pass | Full precision fail |
|---|---:|---:|
| Q4_K_M pass | 332 | 11 |
| Q4_K_M fail | 5 | 79 |

An exact two-sided McNemar test conditions on the 16 discordant pairs. For the
5-recovered versus 11-lost split, `p = 0.2101` (equivalently, the exact
two-sided binomial probability under equal flip directions). The observed
-1.41-point difference is **not statistically significant** at alpha 0.05.
Accordingly, this run does not establish that Q4_K_M is generally superior on
MBPP; it establishes that the direction of the measured configuration gap is
again negative on this benchmark.

## Cross-configuration interpretation

The immediately preceding MBPP single-pass comparison also favored Q4_K_M:
311/427 (`0.7283`) versus 307/427 (`0.7190`), a full-precision change of
-4 problems (-0.94 percentage points; exact McNemar `p = 0.5034`). Best-of-5
now gives a second consecutive MBPP configuration with full-precision
underperformance: -6 problems (-1.41 points; `p = 0.2101`). Neither individual
comparison is significant, but the repeated direction across both frozen
MBPP configurations is reproducible from the committed problem-level
artifacts.

That direction contrasts with all four completed paired HumanEval
configurations: single-pass, best-of-5, adaptive refinement, and fixed-k
refinement each show a full-precision advantage. Thus the project now has a
genuine, reproducible **benchmark-dependent pattern in configuration
sensitivity**: two consecutive MBPP configurations favor Q4_K_M, whereas four
consecutive HumanEval configurations favor full precision. Because backend
and hardware are confounded with precision, this is not evidence that
quantization itself improves MBPP. It is, however, evidence against assuming
that precision/backend effects generalize uniformly across tasks or that a
gap measured on HumanEval can be transferred to MBPP.

This pattern is worth highlighting explicitly in the dissertation discussion
chapter. The defensible claim is that model-serving configuration sensitivity
is benchmark dependent at the observed task level, with enough candidate
diversity to create recoveries and losses in both directions. The stronger
causal claim that weight precision produces the reversal would require a
controlled study holding the inference and execution stacks fixed.
