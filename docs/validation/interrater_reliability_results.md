# Cross-model coding consistency (Codex vs. Claude)

**Analysis date:** 2026-07-24  
**Sample:** 12 blinded cases drawn from the 50-case M7 error taxonomy  
**Coders:** original Codex taxonomy coding and independent Claude coding

## Interpretation and method

This is a **cross-model coding consistency (Codex vs. Claude)** check, not a
study of human coders. The comparison uses the 12 unreconciled Claude ratings
recorded in `interrater_blind_sample.md` and the original Codex ratings in
`interrater_answer_key.md`.

Labels were normalized only for spelling and presentation before comparison:
underscores and hyphens were converted to spaces, and Claude's
`feedback-insufficient` was treated as the rubric-equivalent
`feedback was insufficient`. No substantive labels were reconciled or changed.

Cohen's kappa was calculated as
\(\kappa=(p_o-p_e)/(1-p_e)\), where \(p_o\) is observed agreement and \(p_e\)
is agreement expected from the two coders' marginal label frequencies.
Because the sample contains only 12 deliberately stratified cases, the
statistics are descriptive; no inferential confidence claims are attached.

## Agreement summary

| Coding axis | Agreements | Raw agreement | Expected agreement \(p_e\) | Cohen's \(\kappa\) |
|---|---:|---:|---:|---:|
| Terminal error category | 12/12 | 100.0% | 50.0% | 1.000 |
| Failure mechanism | 12/12 | 100.0% | 38.9% | 1.000 |

The two models assigned exactly the same terminal category and failure
mechanism to every sampled case. This establishes perfect consistency on this
small, stratified sample. It does not establish that every shared code is
correct, particularly where both coders saw the same defective feedback
evidence documented below.

## Confusion matrices

Rows are the original Codex labels and columns are Claude's labels.

### Terminal error category

| Codex \ Claude | Edge case | Logic | Runtime | Syntax | Timeout | Row total |
|---|---:|---:|---:|---:|---:|---:|
| Edge case | 2 | 0 | 0 | 0 | 0 | 2 |
| Logic | 0 | 8 | 0 | 0 | 0 | 8 |
| Runtime | 0 | 0 | 2 | 0 | 0 | 2 |
| Syntax | 0 | 0 | 0 | 0 | 0 | 0 |
| Timeout | 0 | 0 | 0 | 0 | 0 | 0 |
| **Column total** | **2** | **8** | **2** | **0** | **0** | **12** |

### Failure mechanism

| Codex \ Claude | Persistent despite correct feedback | Feedback was insufficient | Fundamentally wrong approach | Row total |
|---|---:|---:|---:|---:|
| Persistent despite correct feedback | 6 | 0 | 0 | 6 |
| Feedback was insufficient | 0 | 2 | 0 | 2 |
| Fundamentally wrong approach | 0 | 0 | 4 | 4 |
| **Column total** | **6** | **2** | **4** | **12** |

## Disagreements and ambiguity

There are no category or mechanism disagreements to list. Consequently, there
is no disagreement-specific confidence or ambiguity adjudication. Claude's
confidence was 5/5 for ten cases and 4/5 for cases 1 and 7. Those lower
confidence ratings did not produce a disagreement.

The absence of disagreements should not be conflated with evidence quality.
Cases 3, 5, and 7 contain a feedback-generation defect visible to both coders,
and case 1 was explicitly considered borderline between a conceptual failure
and persistence despite informative output examples.

## Separate feedback-generation bug investigation

### Confirmed mismatches in requested cases

The frozen M7 JSON confirms that the feedback text cites a different assertion
from the assertion shown at the failure point in the execution traceback:

| Blind case | Task | Iterations affected | Assertion actually failing in execution evidence | Assertion shown in feedback |
|---:|---|---:|---|---|
| 3 | HumanEval/75 | 1–3 | `assert candidate(8) == True` | `assert candidate(5) == False` |
| 5 | HumanEval/146 | 1–3 | `assert candidate([33, -2, -3, 45, 21, 109]) == 2` | `assert candidate([5, -2, 1, -5]) == 0` |
| 7 | HumanEval/127 | 1–3 | `assert candidate((-1, 1), (0, 4)) == "NO"` (iterations 2–3 use the generated function name `intersection`) | `assert candidate((1, 2), (2, 3)) == "NO"` |

This is a real feedback-fidelity bug, independent of the
**cross-model coding consistency (Codex vs. Claude)** calculation. In
HumanEval/75 and HumanEval/146, the assertion supplied as feedback is already
handled by the candidate and therefore conceals the decisive defect. In
HumanEval/127, the cited and actual assertions both expose the same inclusive
length error, so the feedback remains actionable despite being factually
mismatched.

### Cause

The affected frozen HumanEval records execute the complete
`check(candidate)` harness as one test: each iteration reports `0/1`, and its
stored test case contains multiple assertions. The executor's assertion
instrumentation only records an `assertion_expression` when the test case
contains exactly one assertion. For a compound harness it returns no
expression. The template feedback fallback then scans the stored test case and
selects the **first** line beginning with `assert`, rather than extracting the
assertion identified by the traceback. The result is a deterministic
first-assertion label paired with evidence from a later assertion that
actually failed.

The relevant implementation path is:

- `SubprocessExecutor._instrument_assertion`: declines instrumentation unless
  the parsed test case contains exactly one assertion.
- `TemplateFeedbackGenerator._assertion_detail`: falls back to
  `_assertion_line(test.test_case)`.
- `_assertion_line`: returns the first textual `assert` in the compound test.

The current HumanEval loader contains a strict AST-based atomic assertion
splitter. However, the frozen M7 artifacts demonstrably used compound
HumanEval test cases, so the presence of that current safeguard does not
retroactively repair their recorded feedback.

### Audit of all 50 taxonomy cases

The audit compared, for every failed iteration in the 50 coded trajectories:

1. the assertion at the terminal failure frame in stored `stderr`; and
2. the first failed assertion rendered in the stored feedback.

For MBPP, assertions were already executed independently. For HumanEval,
compound harnesses made the fallback vulnerable.

| Audit measure | Result |
|---|---:|
| Taxonomy cases audited | 50 |
| HumanEval cases audited | 14 |
| MBPP cases audited | 36 |
| HumanEval cases with at least one confirmed assertion mismatch | 9/14 (64.3%) |
| All taxonomy cases with at least one confirmed assertion mismatch | 9/50 (18.0%) |
| Confirmed mismatched HumanEval iterations | 22 |
| Comparable HumanEval assertion-feedback pairs | 33 |
| Mismatched comparable pairs | 22/33 (66.7%) |
| MBPP cases affected | 0/36 |

One HumanEval/130 iteration produced exception-oriented feedback without a
rendered failed-assertion entry and was excluded from the pair denominator;
its remaining three iterations matched.

The six additional affected cases are:

| Task | Iterations affected | Assertion actually failing in execution evidence | Assertion shown in feedback |
|---|---:|---|---|
| HumanEval/26 | 1–2 | `assert candidate([1, 2, 3, 2, 4, 3, 5]) == [1, 4, 5]` | `assert candidate([]) == []` |
| HumanEval/64 | 1–2 | `assert vowels_count("quickly") == 2` | `assert candidate("abcde") == 2, "Test 1"` |
| HumanEval/99 | 1–2 | `assert candidate("-15.5") == -16, "Test 3"` | `assert candidate("10") == 10, "Test 1"` |
| HumanEval/125 | 1–2 | `assert candidate("aaabb") == 2` | `assert candidate("Hello world!") == ["Hello","world!"]` |
| HumanEval/135 | 1–2 | `assert candidate([4,8,5,7,3])==4` | `assert candidate([1,2,4,3,5])==3` |
| HumanEval/91 | 1–3 | `assert candidate("Is the sky blue?") == 0, "Test 2"` | `assert candidate("Hello world") == 0, "Test 1"` |

The affected taxonomy cases are HumanEval/26, /64, /75, /91, /99, /125,
/127, /135, and /146. This list includes all seven cases originally coded
`feedback was insufficient`, but it also includes HumanEval/99 and
HumanEval/127, originally coded `persistent despite correct feedback`.
HumanEval/99 merits mechanism recoding review because the displayed assertion
appears to be an already-passing case. HumanEval/127 can reasonably remain
`persistent despite correct feedback` because the incorrectly cited touching
interval is itself a valid counterexample to the same off-by-one defect.
These potential code revisions should be reconciled explicitly rather than
silently changing the frozen original labels.

## Dissertation-use note

Report the first section as **cross-model coding consistency (Codex vs.
Claude)**: category agreement 100%, mechanism agreement 100%, and
\(\kappa=1.00\) on both axes. Report the feedback mismatch separately as an
instrumentation finding. Perfect cross-model consistency does not neutralize
that bug because both coders reviewed the same recorded evidence.

The mismatch also strengthens the taxonomy chapter's distinction between
model non-responsiveness and feedback insufficiency. Some apparent failures to
act on execution feedback were caused upstream: the refinement model was shown
the wrong assertion.
