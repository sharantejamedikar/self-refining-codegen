# M7 error-taxonomy correction log

**Correction date:** 2026-07-24  
**Trigger:** assertion-indexing audit of the frozen M7 HumanEval feedback  
**Scope:** nine affected cases in the 50-case coded taxonomy

## Purpose and decision rule

The frozen M7 HumanEval run sometimes rendered the first assertion in a
compound `check(candidate)` harness even when the traceback showed that a
later assertion actually failed. This log re-examines all nine affected
taxonomy cases using the traceback-matched assertion as the authoritative
failure evidence.

The terminal category remains deterministic: all nine trajectories failed
their single compound HumanEval test with an assertion failure and therefore
remain `logic`. The mechanism was reconsidered using the original definitions:

- `P` — the feedback actually supplied to the model still exposed the
  actionable defect, even if it named a different failing assertion.
- `I` — the supplied feedback did not expose the decisive mismatch identified
  by the traceback-matched assertion.
- `F` — recovery required a fundamentally different algorithmic or
  data-model interpretation rather than a local repair.

This is not a counterfactual assessment of how the model might have responded
if it had received corrected feedback. It classifies the evidence the model
actually received, with the traceback used to determine what truly failed.

## Correction decisions

| Task | Traceback-matched assertion | Feedback-cited assertion | Original | Corrected | Decision and reasoning |
|---|---|---|:---:|:---:|---|
| HumanEval/26 | `candidate([1, 2, 3, 2, 4, 3, 5]) == [1, 4, 5]` | `candidate([]) == []` | Logic / I | Logic / I | **Retain.** The cited empty-list case already passed and did not reveal that every value occurring more than once must be removed, rather than deduplicated to its first occurrence. |
| HumanEval/64 | `vowels_count("quickly") == 2` | `candidate("abcde") == 2` | Logic / I | Logic / I | **Retain.** The cited example already passed and did not identify the candidate's contradictory generated self-test or its treatment of terminal `y`; the actionable failing assertion was absent from feedback. |
| HumanEval/75 | `candidate(8) == True` | `candidate(5) == False` | Logic / I | Logic / I | **Retain.** The cited case already passed and did not expose that prime factors must be counted with multiplicity (`8 = 2 × 2 × 2`), not as distinct primes. |
| HumanEval/91 | `candidate("Is the sky blue?") == 0` | `candidate("Hello world") == 0` | Logic / I | Logic / I | **Retain.** The cited sentence already passed and did not show that a sentence beginning with the letters `Is` must not be counted as beginning with the standalone word `I`. |
| HumanEval/99 | `candidate("-15.5") == -16` | `candidate("10") == 10` | Logic / P | **Logic / I** | **Correct.** The cited integer case already passed and contained no evidence about negative half ties. The model repeated its faulty negative rounding, but the feedback never exposed the decisive `-15.5 → -16` mismatch; calling this persistence despite correct feedback was unsupported. |
| HumanEval/125 | `candidate("aaabb") == 2` | `candidate("Hello world!") == ["Hello", "world!"]` | Logic / I | Logic / I | **Retain.** The cited whitespace-splitting branch already passed and did not reveal the wrong parity used when counting lower-case letters in the no-delimiter branch. |
| HumanEval/127 | `candidate((-1, 1), (0, 4)) == "NO"` | `candidate((1, 2), (2, 3)) == "NO"` | Logic / P | Logic / P | **Retain.** Although the assertion identity was wrong, the cited touching-interval case is itself a direct counterexample to `end - start + 1`; it exposes the same off-by-one defect as the traceback-matched case. The candidate nevertheless retained that formula. |
| HumanEval/135 | `candidate([4, 8, 5, 7, 3]) == 4` | `candidate([1, 2, 4, 3, 5]) == 3` | Logic / I | Logic / I | **Retain.** The cited list has only one inversion and already passed. It did not reveal that the function must return the largest qualifying index when several inversions exist, rather than the first. |
| HumanEval/146 | `candidate([33, -2, -3, 45, 21, 109]) == 2` | `candidate([5, -2, 1, -5]) == 0` | Logic / I | Logic / I | **Retain.** The cited all-small-values case already passed and did not expose the extra requirement that every digit be odd; only the first and last digits should be tested. |

## Net changes

Exactly one of the nine cases changes mechanism:

- HumanEval/99: `P → I`.

No terminal categories change. No case moves into or out of the fundamentally
wrong approach group.

| Mechanism | Original count | Corrected count | Original share | Corrected share | Change |
|---|---:|---:|---:|---:|---:|
| Persistent despite correct feedback (P) | 26 | 25 | 52% | 50% | −1 case / −2 pp |
| Feedback was insufficient (I) | 7 | 8 | 14% | 16% | +1 case / +2 pp |
| Fundamentally wrong approach (F) | 17 | 17 | 34% | 34% | none |
| **Total** | **50** | **50** | **100%** | **100%** |  |

## Effect on the headline finding

The correction does **not materially change** the qualitative finding.
Persistent failure after actionable feedback remains the largest single
mechanism group, but the defensible wording changes from “over half” to
“exactly half” of the coded sample. Feedback insufficiency rises modestly from
14% to 16%, while fundamentally wrong approaches remain 34%.

The correction strengthens the instrumentation caveat: the split between
model non-responsiveness and feedback insufficiency depends on feedback
fidelity. It does not alter the conclusion that local execution feedback alone
failed to resolve a large share of terminal errors.

