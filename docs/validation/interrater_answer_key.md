# M7 error taxonomy: inter-rater answer key

> **Do not consult until the blinded coding sheet is complete.**

This key records the original codes from `error_taxonomy_m7.md`; it is not a
claim that the first rater is necessarily correct. Preserve disagreements for
reconciliation rather than silently overwriting either rating.

## Sampling audit

- Source population: the 50 already-coded cases in `error_taxonomy_m7.md`.
- Selection seed: `20260724`.
- Allocation: 4 HumanEval and 8 MBPP; 8 logic, 2 edge-case, and 2
  runtime; 6 persistent, 2 insufficient-feedback, and 4 wrong-approach.
- Selection was random within the eight benchmark × category × mechanism
  cells needed to obtain that allocation; presentation order was independently
  shuffled with the same recorded seed.

## Original codes

| Case | Problem ID | Original category | Original mechanism | Original rationale |
|---:|---|---|---|---|
| 1 | `MBPP/468` | `edge_case` | fundamentally wrong approach | Solved maximum-product increasing subsequence under a different interpretation from the benchmark and overshot two expected products by orders of magnitude. |
| 2 | `MBPP/452` | `logic` | persistent despite correct feedback | Repeated the conventional cost-minus-sale interpretation although all three actual/expected pairs showed the benchmark expected the opposite argument orientation. |
| 3 | `HumanEval/75` | `logic` | feedback was insufficient | Counted distinct prime factors instead of three prime factors with multiplicity; the displayed `candidate(5) == False` assertion did not reveal that distinction. |
| 4 | `MBPP/299` | `runtime` | fundamentally wrong approach | Treated mixed `(name, value)` records as numeric tuples and kept patching coercion symptoms instead of aggregating values by name. |
| 5 | `HumanEval/146` | `logic` | feedback was insufficient | Required every digit to be odd instead of only the first and last; the displayed all-small-numbers assertion did not exercise the defect. |
| 6 | `MBPP/444` | `logic` | persistent despite correct feedback | Sliced the outer tuple/generator structure rather than trimming `K` values from both ends of each inner tuple, despite complete expected structures. |
| 7 | `HumanEval/127` | `logic` | persistent despite correct feedback | Used inclusive point count (`end-start+1`) instead of interval length (`end-start`) after the touching-interval counterexample was shown. |
| 8 | `MBPP/115` | `runtime` | persistent despite correct feedback | Defined `empty_dict` instead of the required `empty_dit` and repeated it after three explicit `NameError` messages suggested the correction. |
| 9 | `MBPP/429` | `logic` | fundamentally wrong approach | Confused elementwise bitwise AND with Boolean selection, equality tests, and tuple pairing across five candidates. |
| 10 | `HumanEval/113` | `logic` | persistent despite correct feedback | Used each string's self-index instead of substituting its odd-digit count, then returned the identical candidate despite the exact expected sentence. |
| 11 | `MBPP/310` | `edge_case` | persistent despite correct feedback | Preserved spaces in the character tuple and repeated the code after the sole failing expected tuple clearly omitted the space. |
| 12 | `MBPP/603` | `logic` | fundamentally wrong approach | Implemented incorrect value/stride filtering rather than the position-based ludic sieve, collapsing the output to `[1]`. |

## Comparison worksheet

| Case | Category agree? | Mechanism agree? | Reconciliation note |
|---:|:---:|:---:|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |
| 6 |  |  |  |
| 7 |  |  |  |
| 8 |  |  |  |
| 9 |  |  |  |
| 10 |  |  |  |
| 11 |  |  |  |
| 12 |  |  |  |

Report raw agreement separately for terminal category and failure mechanism.
For each axis, also compute Cohen's kappa from the unreconciled 12 paired
ratings. With only 12 cases and a deliberately stratified sample, present
kappa descriptively alongside the confusion matrix and exact disagreement
list; do not attach inferential confidence claims to this small check.

