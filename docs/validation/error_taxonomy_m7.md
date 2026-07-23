# M7 adaptive-hybrid error taxonomy

**Analysis date:** 2026-07-23  
**Scope:** terminal failures from the M7 Qwen-2.5-Coder-7B Q4_K_M local
development runs  
**Sample size:** 50 of 97 terminal failures

## Evidence and denominator

This analysis uses the frozen per-problem JSON traces from:

- [HumanEval adaptive hybrid run](../../experiments/results/20260720T110814.447169Z_m7_quantized_local_development_hybrid_refinement_adaptive_humaneval_full/)
- [MBPP adaptive hybrid run](../../experiments/results/20260720T112112.959147Z_m7_quantized_local_development_hybrid_refinement_adaptive_mbpp_full/)

The evidence corrects an important denominator ambiguity. HumanEval had 28
iteration-1 failures (`164 - 136`), but refinement rescued seven of them. It
therefore had **21 terminal failures**, not 28. MBPP had 76 terminal failures.
The sampling population is consequently 97 terminal failures (21 HumanEval +
76 MBPP).

These are quantized-local development artifacts. They support process and
qualitative error analysis, but, under the project protocol, they are not
full-precision dissertation performance estimates.

## Coding method

The unit of analysis is one problem's complete adaptive-refinement trajectory.
The error category is the deterministic category at the terminal iteration.
For MBPP/123, `runtime (timeout→runtime)` records both its terminal category
and its unique timeout exposure. Iteration count is the number of generated
candidates executed before convergence.

The three mutually exclusive mechanism codes were assigned by reading the
prompt, every candidate, execution result, feedback message, and convergence
decision:

- **Persistent despite correct feedback (P):** the feedback identified the
  actionable failing assertion, actual/expected mismatch, or exception, but
  the next candidate repeated the defect, introduced a closely related defect,
  or reverted.
- **Feedback was insufficient (I):** the recorded feedback did not expose the
  decisive mismatch. This includes HumanEval's single compound `check`
  diagnostic when the displayed first assertion was not necessarily the one
  that failed.
- **Fundamentally wrong approach (F):** the candidate used the wrong
  mathematical/algorithmic interpretation or data model, and local correction
  of the reported symptom was not enough to recover the required method.

The distinction is about the observed trajectory, not an intrinsic difficulty
label for the benchmark task. Coding was performed once by one reviewer; the
percentages are descriptive and should not be presented as inter-rater
validated.

## Post-hoc assertion-mismatch correction

**Corrected 2026-07-24.** A frozen-record audit found that nine sampled
HumanEval trajectories rendered the first assertion in a compound harness
rather than the assertion identified by the traceback. All nine were manually
re-examined against the traceback-matched assertion. Eight labels were
retained; HumanEval/99 changed from `P` to `I`. No terminal category changed.

The complete, non-silent reconciliation is recorded in
[the M7 error-taxonomy correction log](error_taxonomy_correction_log.md).
Corrected labels and statistics are used throughout the remainder of this
document.

| Task | Original label | Corrected label | Outcome |
|---|:---:|:---:|---|
| HumanEval/26 | Logic / I | Logic / I | Retained: cited empty-list case did not expose remove-all-duplicates semantics. |
| HumanEval/64 | Logic / I | Logic / I | Retained: cited `abcde` case did not expose the traceback-matched `quickly` failure. |
| HumanEval/75 | Logic / I | Logic / I | Retained: cited input 5 did not expose prime-factor multiplicity required by input 8. |
| HumanEval/91 | Logic / I | Logic / I | Retained: cited `Hello world` case did not expose the standalone-word-`I` defect. |
| HumanEval/99 | Logic / P | **Logic / I** | Corrected: cited integer case passed and did not expose negative half-tie rounding. |
| HumanEval/125 | Logic / I | Logic / I | Retained: cited whitespace branch did not expose wrong alphabet-index parity. |
| HumanEval/127 | Logic / P | Logic / P | Retained: wrongly cited touching-interval case still exposed the same `+1` defect. |
| HumanEval/135 | Logic / I | Logic / I | Retained: cited single-inversion case did not distinguish first from largest inversion. |
| HumanEval/146 | Logic / I | Logic / I | Retained: cited small-number case did not expose the all-digits-versus-end-digits defect. |

## Sampling

Allocation was approximately proportional to the 97-failure population while
retaining all observed categories and convergence reasons. Within each
non-empty benchmark × terminal-category × convergence-reason stratum, task IDs
were selected with Python's `random.Random(20260723)`. One pre-specified
within-stratum swap replaced an ordinary MBPP runtime/oscillation case with
MBPP/123, the population's only timeout-exposed terminal failure. HumanEval
contributes 14 cases and MBPP 36.

There were no terminal syntax or timeout failures. No terminal-failure
trajectory contained a syntax error. One MBPP trajectory, MBPP/123, changed
from timeout to runtime and was deliberately retained as the timeout-exposed
case. Empty strata are reported as observed zeros rather than populated
artificially.

| Benchmark | Terminal category | Oscillation | Stagnation | Max iterations | Population total |
|---|---:|---:|---:|---:|---:|
| HumanEval | Logic | 14 | 7 | 0 | 21 |
| MBPP | Logic | 30 | 11 | 5 | 46 |
| MBPP | Edge case | 11 | 7 | 1 | 19 |
| MBPP | Runtime | 8 | 2 | 1 | 11 |
| Both | Syntax | 0 | 0 | 0 | 0 |
| Both | Timeout (terminal) | 0 | 0 | 0 | 0 |
| **Terminal-failure population** |  | **63** | **27** | **7** | **97** |

The resulting coded-sample allocation is:

| Benchmark | Terminal category | Oscillation | Stagnation | Max iterations | Sample total |
|---|---:|---:|---:|---:|---:|
| HumanEval | Logic | 9 | 5 | 0 | 14 |
| MBPP | Logic | 14 | 5 | 2 | 21 |
| MBPP | Edge case | 5 | 3 | 1 | 9 |
| MBPP | Runtime | 4 | 1 | 1 | 6 |
| Both | Syntax | 0 | 0 | 0 | 0 |
| Both | Timeout (terminal) | 0 | 0 | 0 | 0 |
| **Total** |  | **32** | **14** | **4** | **50** |

## Summary results

### Failure mechanism

| Mechanism | Count | Share of coded sample |
|---|---:|---:|
| Persistent despite correct feedback (P) | 25 | 50% |
| Feedback was insufficient (I) | 8 | 16% |
| Fundamentally wrong approach (F) | 17 | 34% |
| **Total** | **50** | **100%** |

Exactly half of the sampled failures persisted even when the execution
feedback contained the information needed for a local repair. HumanEval/46 is
the clearest example: the failing `fib4(5) == 4` assertion was supplied, yet
the model emitted byte-for-byte identical off-by-one loop logic and
immediately oscillated. This suggests that feedback availability alone is not
sufficient; the model must also attend to and correctly translate the
diagnostic.

The eight insufficient-feedback cases are all HumanEval cases. HumanEval is
executed as one compound `check(candidate)` test, so its diagnostic pass rate
is `0/1` and the reported assertion can be an earlier, passing assertion rather
than the actual point of failure. MBPP's independent assertions expose
actual/expected values per case. The benchmark difference is therefore partly
an instrumentation effect and should not be interpreted as evidence that
HumanEval inherently elicits worse feedback.

One third of the sample required a conceptual change rather than a local patch:
examples include confusing row averages with column averages (MBPP/615),
implementing a predicate instead of the nth octagonal-number formula
(MBPP/59), and lacking the ludic-number sieve (MBPP/603). Longer feedback that
only repeats observed outputs is unlikely to fix this class reliably.

### Deterministic terminal category

| Terminal category | Count | Share |
|---|---:|---:|
| Logic | 35 | 70% |
| Edge case | 9 | 18% |
| Runtime | 6 | 12% |
| Timeout | 0 | 0% |
| Syntax | 0 | 0% |
| **Total** | **50** | **100%** |

Logic dominates because syntax and most runtime defects are either absent at
generation time or corrected before termination. The absence of terminal
syntax errors is itself a result: code extraction plus the code-specialized
model made syntactic validity comparatively tractable. The sole timeout-exposed
sample, MBPP/123, improved from timeout to an `IndexError`; feedback changed the
failure mode but did not produce a valid efficient algorithm.

### Convergence reason

| Convergence reason | Count | Share |
|---|---:|---:|
| Oscillation | 32 | 64% |
| Stagnation | 14 | 28% |
| Max iterations | 4 | 8% |
| **Total** | **50** | **100%** |

Adaptive stopping usually terminated unproductive refinement before the
five-iteration cap: 92% of this stratified sample ended through oscillation or
stagnation. In many oscillation cases the second candidate was identical to
the first; in others the model alternated between two incorrect local patches.

## Full coded sample

`Cat.` is the terminal deterministic category; `P`, `I`, and `F` use the
mechanism definitions above.

| # | Task | Cat. | Convergence | Iter. | Code | One-line diagnosis |
|---:|---|---|---|---:|:---:|---|
| 1 | HumanEval/26 | Logic | Oscillation | 2 | I | Kept first occurrences instead of removing every duplicated value; the compound-test feedback displayed an empty-list assertion that this code already satisfied. |
| 2 | HumanEval/46 | Logic | Oscillation | 2 | P | Repeated identical off-by-one Fib4 initialization/loop logic after feedback explicitly identified `fib4(5) == 4`. |
| 3 | HumanEval/64 | Logic | Oscillation | 2 | I | Added incorrect self-tests at module scope (for example `fly == 0`), while the feedback surfaced only the opaque compound-check failure. |
| 4 | HumanEval/99 | Logic | Oscillation | 2 | I | Repeated incorrect half-away-from-zero handling for negative values, but feedback cited the already-passing integer case instead of the traceback-matched `-15.5 → -16` failure. |
| 5 | HumanEval/113 | Logic | Oscillation | 2 | P | Used each string's self-index instead of substituting its odd-digit count, then returned the identical candidate despite the exact expected sentence. |
| 6 | HumanEval/125 | Logic | Oscillation | 2 | I | Counted even alphabet indices rather than the specified odd indices; the displayed whitespace example was already handled correctly. |
| 7 | HumanEval/135 | Logic | Oscillation | 2 | I | Returned the first inversion rather than the largest inversion index; feedback displayed the example that already returned 3. |
| 8 | HumanEval/145 | Logic | Oscillation | 2 | P | Ignored the sign when summing digits, so negative values tied incorrectly, and repeated the code after the required ordering was shown. |
| 9 | HumanEval/163 | Logic | Oscillation | 2 | P | Generated all even integers in the interval rather than even digits 2–8, despite feedback showing that input `(2, 10)` must exclude 10. |
| 10 | HumanEval/75 | Logic | Stagnation | 3 | I | Counted distinct prime factors instead of three prime factors with multiplicity; the displayed `candidate(5) == False` assertion did not reveal that distinction. |
| 11 | HumanEval/91 | Logic | Stagnation | 3 | I | Varied case and whitespace checks without isolating sentence-start token `I`; the diagnostic exposed only test labels, not the decisive sentence/output. |
| 12 | HumanEval/127 | Logic | Stagnation | 3 | P | Used inclusive point count (`end-start+1`) instead of interval length (`end-start`) after the touching-interval counterexample was shown. |
| 13 | HumanEval/130 | Logic | Stagnation | 4 | P | Fixed the `IndexError` but replaced `tri(i+1)` with a duplicate `tri(i-1)`, repeatedly producing the wrong odd recurrence after the expected list was shown. |
| 14 | HumanEval/146 | Logic | Stagnation | 3 | I | Required every digit to be odd instead of only the first and last; the displayed all-small-numbers assertion did not exercise the defect. |
| 15 | MBPP/83 | Logic | Oscillation | 3 | P | Corrected uppercase to lowercase but retained the wrong ASCII offset, despite exact actual/expected characters for all tests. |
| 16 | MBPP/87 | Logic | Oscillation | 3 | P | Changed last-dictionary-wins merging into lists of duplicate values, even though feedback showed that the first dictionary's value must be retained. |
| 17 | MBPP/124 | Logic | Oscillation | 4 | F | Misread the second argument as a real imaginary component and alternated invalid `atan2`/`complex(a,b)` constructions instead of taking the phase of `a+b`. |
| 18 | MBPP/290 | Logic | Oscillation | 3 | P | Progressed from a list of longest lists to `(length, [list])` but failed to remove the extra nesting shown explicitly in every expected value. |
| 19 | MBPP/430 | Logic | Oscillation | 4 | F | Guessed small vertex/directrix formula variants whose scale was incompatible with all expected outputs, never recovering the benchmark's intended formula. |
| 20 | MBPP/444 | Logic | Oscillation | 3 | P | Sliced the outer tuple/generator structure rather than trimming `K` values from both ends of each inner tuple, despite complete expected structures. |
| 21 | MBPP/452 | Logic | Oscillation | 2 | P | Repeated the conventional cost-minus-sale interpretation although all three actual/expected pairs showed the benchmark expected the opposite argument orientation. |
| 22 | MBPP/584 | Logic | Oscillation | 2 | P | Returned a list of `(word,start)` pairs instead of the required `"start-end: word"` string explicitly present in every expected value. |
| 23 | MBPP/592 | Logic | Oscillation | 4 | F | Tried unrelated binomial products and never derived the consecutive-coefficient identity, even after several complete input/output examples. |
| 24 | MBPP/603 | Logic | Oscillation | 3 | F | Implemented incorrect value/stride filtering rather than the position-based ludic sieve, collapsing the output to `[1]`. |
| 25 | MBPP/612 | Logic | Oscillation | 3 | P | Returned tuples and then extra nesting instead of transposing to a list of lists, despite exact structural diffs including the three-column case. |
| 26 | MBPP/615 | Logic | Oscillation | 2 | F | Averaged each row instead of each column and repeated the approach although expected column averages were supplied. |
| 27 | MBPP/644 | Logic | Oscillation | 2 | P | Reversed through index `k` rather than the first `k` elements and repeated the off-by-one implementation after exact list diffs. |
| 28 | MBPP/765 | Logic | Oscillation | 3 | F | Used ad hoc bit tests rather than generating the nth polite number, with no trajectory step approaching the required sequence. |
| 29 | MBPP/59 | Logic | Stagnation | 4 | F | Treated `is_octagonal(n)` as a membership predicate rather than returning the nth octagonal number, despite numeric expected outputs. |
| 30 | MBPP/235 | Logic | Stagnation | 3 | F | Applied an unbounded fixed 32-bit alternating mask rather than setting even-position bits only within the number's active width. |
| 31 | MBPP/252 | Logic | Stagnation | 4 | P | Fixed scalar handling but kept wrapping the polar-coordinate tuple in a list after every expected value showed a bare tuple. |
| 32 | MBPP/311 | Logic | Stagnation | 3 | F | Shifted away the original number while searching from the right, never implementing “set the leftmost zero below the most-significant set bit.” |
| 33 | MBPP/777 | Logic | Stagnation | 3 | P | Summed only values occurring once rather than summing each distinct value once, despite exact totals for repeated-element inputs. |
| 34 | MBPP/429 | Logic | Max iterations | 5 | F | Confused elementwise bitwise AND with Boolean selection, equality tests, and tuple pairing across five candidates. |
| 35 | MBPP/630 | Logic | Max iterations | 5 | P | Expanded from four to eight neighbors but repeatedly omitted the center coordinate that the complete expected 3×3 grids included. |
| 36 | MBPP/20 | Edge case | Oscillation | 2 | F | Used a Mersenne-number-style bit test instead of the Woodall-number definition, passing only one of three cases. |
| 37 | MBPP/310 | Edge case | Oscillation | 2 | P | Preserved spaces in the character tuple and repeated the code after the sole failing expected tuple clearly omitted the space. |
| 38 | MBPP/443 | Edge case | Oscillation | 2 | P | Interpreted “largest negative” numerically as closest to zero, while two exact diffs showed the benchmark expected the most negative value. |
| 39 | MBPP/468 | Edge case | Oscillation | 2 | F | Solved maximum-product increasing subsequence under a different interpretation from the benchmark and overshot two expected products by orders of magnitude. |
| 40 | MBPP/626 | Edge case | Oscillation | 4 | F | Used an equilateral-triangle area formula instead of the maximum triangle in a semicircle and then alternated only the zero-radius return convention. |
| 41 | MBPP/138 | Edge case | Stagnation | 3 | F | Tested whether the number itself was a power of two rather than representable as a sum of distinct non-zero powers. |
| 42 | MBPP/306 | Edge case | Stagnation | 3 | F | Added `a[k]` to the subsequence ending exactly at `index` instead of optimizing over the permitted prefix, leaving the same 111-versus-11 failure. |
| 43 | MBPP/610 | Edge case | Stagnation | 3 | P | Removed zero-based index `L` rather than the kth/one-based element, despite two exact lists revealing the off-by-one shift. |
| 44 | MBPP/769 | Edge case | Max iterations | 5 | P | Found the symmetric difference by iteration 2 but destroyed the benchmark's required list order with sets/sorting through iteration 5. |
| 45 | MBPP/115 | Runtime | Oscillation | 2 | P | Defined `empty_dict` instead of the required `empty_dit` and repeated it after three explicit `NameError` messages suggested the exact correction. |
| 46 | MBPP/123 | Runtime (timeout→runtime) | Oscillation | 3 | F | Replaced an \(O(n^2)\) divisor search after timeout with an unsafe bounded cache, then repeated an out-of-range access on divisor sums above `limit`. |
| 47 | MBPP/398 | Runtime | Oscillation | 3 | P | Returned per-number digit sums instead of their aggregate and still called `abs()` on nested lists after exact values and type errors exposed both issues. |
| 48 | MBPP/763 | Runtime | Oscillation | 2 | P | Called in-place `.sort()` on tuple inputs and repeated the implementation after all three tests reported the same `AttributeError`. |
| 49 | MBPP/617 | Runtime | Stagnation | 3 | P | Applied arithmetic to tuple-valued `steps`, then mistakenly type-checked `d`, despite the repeated `int % tuple` exception. |
| 50 | MBPP/299 | Runtime | Max iterations | 5 | F | Treated mixed `(name, value)` records as numeric tuples and kept patching coercion symptoms instead of aggregating values by name. |

## Implications for the dissertation

1. **Separate feedback fidelity from model responsiveness.** The 16%
   insufficient-feedback share is concentrated in HumanEval's compound test
   harness, whereas 50% persist after actionable feedback. These are different
   failure sources and should not be combined as “refinement failed.”
2. **Report transition success, not only terminal categories.** MBPP/123
   demonstrates that feedback can remove a timeout while leaving a runtime
   defect. Such transitions are partial progress even when pass@1 is unchanged.
3. **Use targeted feedback for structural mismatches.** Many persistent cases
   are return-shape, ordering, naming, or off-by-one defects. A feedback
   strategy that explicitly contrasts candidate and required structures may
   be more useful than a generic “reconsider the core algorithm” instruction.
4. **Do not expect trace length alone to solve conceptual failures.** The 34%
   fundamentally-wrong-approach group needs problem reinterpretation,
   algorithm retrieval, or a fresh sample rather than repeated local repair.
5. **Treat the mechanism percentages as qualitative M7 evidence.** The sample
   is stratified rather than a simple random sample and is single-coded;
   percentages characterize these 50 cases and are not population-weighted
   estimates with inferential confidence intervals.
