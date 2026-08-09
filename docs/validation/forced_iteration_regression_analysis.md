# Forced-iteration regression deep dive

## Scope and definition

This analysis asks what happens when fixed-iteration refinement continues after
a candidate has already passed every persisted test. A **regression case** is a
problem that passed at least one iteration before iteration 5 but failed at
iteration 5. The unit counted below is a problem-run observation, because the
same task can regress independently under two inference configurations.

The committed fixed-run evidence comprises four benchmark/configuration
datasets:

| Dataset | Authoritative artifact | Regressions | Unique task IDs |
|---|---|---:|---:|
| Q4_K_M HumanEval-164 | [`20260724...fixed_humaneval_full`](../../experiments/results/20260724T151654.164295Z_m7_quantized_local_development_hybrid_refinement_fixed_humaneval_full/) | 5 | 5 |
| Q4_K_M MBPP-427 | [`20260721...fixed_mbpp_full`](../../experiments/results/20260721T102049.383499Z_m7_quantized_local_development_hybrid_refinement_fixed_mbpp_full/) | 13 | 13 |
| Full-precision HumanEval-164 | [`20260808...fixed_humaneval_full`](../../experiments/results/20260808T220435.152210Z_cluster_qwen_hf_hybrid_refinement_fixed_humaneval_full/) | 5 | 5 |
| Full-precision MBPP-427 | [`20260809...fixed_mbpp_full`](../../experiments/results/20260809T162731.848774Z_cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full/) | 18 | 18 |
| **Total** |  | **41 observations** | **33 tasks** |

The Q4_K_M artifacts are labelled `quantized_local_development` because
Q4_K_M was explicitly a local-development configuration, although these two
runs used the full frozen benchmark sets. There is no separately persisted
fixed-k dev-split artifact in the committed results. The earlier dev-set
reports document related but different events: HumanEval/83 changed outcome
between feedback strategies, and MBPP/734 lost partial test credit before
oscillating. Neither passed all tests and then failed because fixed mode forced
another iteration, so neither is included in the case count. This distinction
prevents cross-strategy and partial-pass regressions from being silently mixed
with the phenomenon defined here.

The July 20 Q4_K_M HumanEval fixed run is also excluded: its compound-harness
feedback was confounded and it was superseded by the corrected July 24
artifact. The supersession is documented in
[`m7_humaneval_feedback_correction.md`](m7_humaneval_feedback_correction.md).

## Method

For each qualifying record, the comparison endpoints are the **last iteration
that passed** and iteration 5. “Before → after” is therefore the deterministic
classifier transition at those endpoints, not a manual judgement. Character
edit distance is exact Levenshtein distance over the extracted code strings.
The diff summary describes the semantic change in the corresponding unified
line diff. Character and line changes are final minus last-successful code.

The feedback signal was audited in two places: the `feedback` stored on the
last-successful iteration and the next generation's rendered prompt. In every
one of the 41 observations, the feedback was `All assertions passed.` and was
present in the next prompt, immediately followed by the instruction `Return a
corrected complete solution.` Thus the execution result itself was accurate;
the misleading signal came from asking for a correction despite success.

## Case-level results

### Q4_K_M HumanEval-164

All five candidates first passed at iteration 1 and never passed again. Each
transition is success → logic at iteration 5.

| Task | Last pass → final | Edit distance | Size change (chars; lines) | Material diff | Trigger signal |
|---|---:|---:|---:|---|---|
| HumanEval/100 | 1 → 5 | 455 | +454; +13 | Added a long docstring and changed the even-step increment from `+2` to `+1`. | Passed, but asked to “correct” |
| HumanEval/134 | 1 → 5 | 45 | +45; 0 | Added a preceding-character restriction to the final-space condition. | Passed, but asked to “correct” |
| HumanEval/138 | 1 → 5 | 236 | +235; +6 | Added a docstring and raised the valid lower bound from 8 to 16. | Passed, but asked to “correct” |
| HumanEval/160 | 1 → 5 | 183 | +99; +3 | Replaced Python-expression evaluation with left-to-right operator application, losing precedence. | Passed, but asked to “correct” |
| HumanEval/81 | 1 → 5 | 54 | -52; -2 | Removed the `D-` branch and mapped all non-positive GPAs to `E`. | Passed, but asked to “correct” |

### Q4_K_M MBPP-427

Ten of the thirteen last passed at iteration 4, two at iteration 1, and one at
iteration 2. The repeated pattern for the iteration-4 cases was alternating
pass/fail output under unchanged “all passed, correct it” prompting.

| Task | Before → after | Last pass → final | Edit distance | Size change (chars; lines) | Material diff |
|---|---|---:|---:|---:|---|
| MBPP/143 | success → edge-case | 4 → 5 | 28 | -28; 0 | Stopped counting the outer list itself. |
| MBPP/160 | success → edge-case | 1 → 5 | 564 | +545; +31 | Replaced a six-line bounded search with a 37-line Diophantine/modular-inverse implementation. |
| MBPP/249 | success → edge-case | 4 → 5 | 8 | -8; 0 | Removed sorting from the set intersection result. |
| MBPP/265 | success → logic | 4 → 5 | 13 | +12; 0 | Changed stride-based splitting to contiguous chunks. |
| MBPP/393 | success → logic | 4 → 5 | 46 | +35; 0 | Changed the required `(length, list)` tuple into a list-or-lists return. |
| MBPP/437 | success → logic | 4 → 5 | 6 | -6; 0 | Swapped one-based even positions for zero-based even indices. |
| MBPP/446 | success → logic | 4 → 5 | 47 | -44; -1 | Returned the frequency dictionary rather than the total count. |
| MBPP/465 | success → logic | 4 → 5 | 10 | -6; 0 | Filtered empty strings instead of `None` values. |
| MBPP/624 | success → logic | 4 → 5 | 2 | +2; 0 | Returned an uppercase predicate rather than the uppercase string. |
| MBPP/722 | success → edge-case | 4 → 5 | 2 | -2; 0 | Changed inclusive height/weight thresholds to strict thresholds. |
| MBPP/757 | success → logic | 1 → 5 | 47 | +34; +2 | Added a `seen` set but retained division by two, undercounting reversed pairs. |
| MBPP/758 | success → edge-case | 2 → 5 | 8 | +8; 0 | Sorted each sublist before counting, incorrectly merging permutations. |
| MBPP/809 | success → logic | 4 → 5 | 1 | 0; 0 | Reversed the tuple comparison from `>` to `<`. |

For all thirteen rows, the trigger signal is identical to the HumanEval rows:
the last-successful iteration supplied `All assertions passed.`, followed by
an instruction to return a corrected solution.

### Full-precision HumanEval-164

| Task | Before → after | Last pass → final | Edit distance | Size change (chars; lines) | Material diff | Trigger signal |
|---|---|---:|---:|---:|---|---|
| HumanEval/74 | success → logic | 4 → 5 | 1 | -1; 0 | Changed the tie-preserving `<=` comparison to `<`. | Passed, but asked to “correct” |
| HumanEval/81 | success → logic | 1 → 5 | 1 | +1; 0 | Changed `gpa > 0.0` to `gpa >= 0.0`, misclassifying zero. | Passed, but asked to “correct” |
| HumanEval/109 | success → logic | 1 → 5 | 64 | +64; +1 | Added a `start` constraint that rejects valid bracket sequences. | Passed, but asked to “correct” |
| HumanEval/126 | success → logic | 4 → 5 | 25 | -25; 0 | Changed the three-equal-elements check into a two-equal-elements check. | Passed, but asked to “correct” |
| HumanEval/160 | success → logic | 1 → 5 | 177 | +84; +3 | Replaced expression evaluation with left-to-right operator application, losing precedence. | Passed, but asked to “correct” |

HumanEval/81 and HumanEval/160 therefore replicate at the task level across
Q4_K_M and full precision. The exact mutations are not identical for /81, but
both alter the low-GPA boundary; both /160 outputs independently replace
precedence-aware expression evaluation with left-to-right reduction.

### Full-precision MBPP-427

Fourteen of the 18 cases last passed at iteration 4, two at iteration 3, one at
iteration 2, and one at iteration 1. Thirteen trajectories alternate between
failure and success before failing at iteration 5. Character and line changes
compare the last passing code with iteration 5.

| Task | Before → after | Trajectory | Last pass → final | Edit distance | Size change (chars; lines) |
|---|---|---:|---:|---:|---:|
| MBPP/91 | success → edge-case | `FPFPF` | 4 → 5 | 72 | -66; -3 |
| MBPP/249 | success → edge-case | `FPFPF` | 4 → 5 | 8 | -8; 0 |
| MBPP/252 | success → logic | `FFFPF` | 4 → 5 | 76 | -76; 0 |
| MBPP/259 | success → logic | `FPFPF` | 4 → 5 | 29 | -29; 0 |
| MBPP/265 | success → logic | `FPFPF` | 4 → 5 | 13 | +12; 0 |
| MBPP/290 | success → logic | `FPFFF` | 2 → 5 | 27 | -27; 0 |
| MBPP/391 | success → logic | `FPFPF` | 4 → 5 | 62 | +19; +1 |
| MBPP/393 | success → logic | `FPFPF` | 4 → 5 | 9 | -9; 0 |
| MBPP/429 | success → logic | `FFPFF` | 3 → 5 | 15 | +5; 0 |
| MBPP/437 | success → logic | `FPFPF` | 4 → 5 | 1 | 0; 0 |
| MBPP/475 | success → logic | `FFPFF` | 3 → 5 | 14 | -14; 0 |
| MBPP/592 | success → logic | `PFFFF` | 1 → 5 | 51 | +50; 0 |
| MBPP/595 | success → edge-case | `FPFPF` | 4 → 5 | 28 | -24; 0 |
| MBPP/596 | success → logic | `FPFPF` | 4 → 5 | 83 | +74; +3 |
| MBPP/624 | success → logic | `FPFPF` | 4 → 5 | 10 | +10; 0 |
| MBPP/722 | success → edge-case | `FPFPF` | 4 → 5 | 2 | -2; 0 |
| MBPP/750 | success → logic | `FPFPF` | 4 → 5 | 36 | +1; 0 |
| MBPP/776 | success → edge-case | `FPFPF` | 4 → 5 | 269 | -265; -5 |

Six tasks regress in both MBPP configurations: MBPP/249, /265, /393, /437,
/624, and /722. The exact trajectories match for all six, although this does
not make the two backend/precision runs independent replications. As in the
other conditions, every successful iteration supplied `All assertions
passed.` before the next prompt nevertheless requested a correction.

## Cross-dataset patterns

### 1. Prompt semantics are the only universal correlate

All 41 observations share the same causal precondition visible in the logs:
fixed mode continues after success, reports that all assertions passed, and
still asks for a “corrected” solution. There is no new failing assertion,
traceback, error category, or counterexample to condition the next generation.
The model is therefore not repairing an observed defect; it is sampling a new
interpretation under an instruction that presupposes a defect. This is best
described as **uninformed post-success mutation**, not erroneous execution
feedback.

The resulting failures are exclusively logic (31/41) or edge-case (10/41).
None is syntax, runtime, or timeout. That is consistent with all final programs
remaining executable while a small semantic choice changes.

### 2. Regression position is bimodal and dataset-dependent

The last successful iteration was iteration 4 in 26/41 cases, iteration 1 in
11/41, iteration 2 in 2/41, and iteration 3 in 2/41. This is not evidence that
a particular iteration intrinsically causes regression: the endpoint is
defined as a failure at forced iteration 5, and the benchmark trajectories
differ.

- Q4_K_M HumanEval: all 5 passed only at iteration 1, then failed at iterations
  2–5.
- Q4_K_M MBPP: 10/13 last passed at iteration 4; several alternate between
  success and failure, showing prompt-sensitive resampling rather than
  monotonic refinement.
- Full-precision HumanEval: 3/5 last passed at iteration 1 and 2/5 at iteration
  4.
- Full-precision MBPP: 14/18 last passed at iteration 4; 13/18 trajectories
  alternated between failure and success before the final failure.

The meaningful timing result is therefore that damage can occur immediately
after success and can also recur after later recovery. Success-priority
stopping prevents both.

### 3. Most regressions need only a small semantic mutation

Across the 41 observations, median character edit distance is 28 (range
1–564); 14/41 are at most 10 edits and 28/41 are at most 50. Median net length
change is zero characters. Twenty final programs are longer, 19 are shorter,
and two are unchanged in character count. There is consequently no
consistent length direction.

Two large rewrites (Q4 HumanEval/100 and MBPP/160) inflate the mean edit
distance; across all 41 cases the mean is 69 characters. These rewrites show
that gratuitous elaboration can regress. However, the one-character
regressions in MBPP/809, HumanEval/74, and
HumanEval/81 demonstrate that complexity growth is not required. Most errors
are boundary/operator, return-shape, ordering, or interpretation changes.

### 4. Initial error category differs by benchmark

Fifteen of 41 observations had already succeeded at iteration 1; the other 26
began as logic (17), edge-case (8), or runtime (1). Among ever-solved
candidates in each run, the observed regression proportions by initial
classifier category were:

| Dataset | Initial success | Initial logic | Initial edge-case | Initial runtime |
|---|---:|---:|---:|---:|
| Q4_K_M HumanEval | 5/136 (3.7%) | 0/4 | — | 0/3 |
| Q4_K_M MBPP | 4/310 (1.3%) | 6/22 (27.3%) | 3/12 (25.0%) | 0/6 |
| Full-precision HumanEval | 5/141 (3.5%) | 0/4 | — | 0/3 |
| Full-precision MBPP | 1/307 (0.3%) | 11/24 (45.8%) | 5/14 (35.7%) | 1/7 (14.3%) |

These denominators are restricted to problems that succeeded at least once,
because never-solved problems cannot exhibit success regression. The MBPP
association suggests that tasks requiring an earlier repair may remain less
stable under further sampling. It should not be generalized: the denominators
remain small, the pattern is absent in HumanEval, and initial execution
category is not an intrinsic task-complexity label.

No committed metadata provides an independent “original problem category” or
validated task-complexity measure. Generated-code length and AST size are poor
proxies and the case diffs already contradict a monotonic complexity account.
Assigning semantic problem categories retrospectively would add an unplanned,
subjective annotation layer, so this report does not do so.

### 5. Apparent benchmark trend

MBPP has more raw regressions than HumanEval at both configurations: 13 versus
5 under Q4_K_M and 18 versus 5 under full precision. Among ever-solved tasks,
the corresponding proportions are 13/350 (3.7%) versus 5/143 (3.5%), and
18/352 (5.1%) versus 5/148 (3.4%). Thus the full-precision pair shows a larger
rate as well as a larger count, whereas the Q4_K_M rates are nearly equal.

This apparent benchmark difference is worth further investigation, especially
because MBPP exposes atomic tests and more initially failing candidates later
recover. It is not evidence that benchmark identity causes regression. MBPP
has 427 tasks versus HumanEval's 164, the outcome sample contains only 41
selected cases, HumanEval uses a compound harness, and all observations come
from one model family, temperature, and seed. A controlled follow-up would
compare regression proportions with uncertainty intervals across additional
seeds while holding the execution and inference stack fixed.

## Interpretation and limitations

The evidence strongly supports the protocol decision to rank success above
all other convergence criteria. Under the ever-solved metric, fixed iteration
does not erase a prior success; under final-only evaluation it creates 41
observed failures that adaptive success stopping would have prevented. The
logs identify a concrete mechanism: correct success feedback is paired with a
contradictory request for correction and no new diagnostic information.

This is a small, selected sample: 41 problem-run observations and 33
unique tasks across only two benchmarks, one model family, one temperature,
and two end-to-end inference configurations. The cases are selected on the
outcome being explained, so their internal frequencies are descriptive, not
population estimates. Q4_K_M versus full precision is also confounded by
backend and hardware. Repeated tasks show reproducibility of the phenomenon,
not independence, and the MBPP tests and HumanEval harness expose different
numbers and kinds of assertions. These data justify success-priority stopping
and the “uninformed mutation” mechanism, but they do not establish a stable
per-category regression rate or a causal effect of quantization, code length,
or task complexity.

## Reproducibility note

This analysis uses only persisted JSON fields (`iterations`, `classification`,
`execution`, `feedback`, `generation.code`, and the rendered prompt); no
generated code was re-executed during analysis. Before analysis, the CPU-only
repository test suite completed with 128 passing tests in 6.14 seconds.
