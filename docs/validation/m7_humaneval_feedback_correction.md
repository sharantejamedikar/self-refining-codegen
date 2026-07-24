# M7 HumanEval feedback correction

**Correction completed:** 2026-07-24  
**Scope:** M7 HumanEval-164 hybrid refinement, adaptive and fixed-k=5  
**Status:** corrected reruns are authoritative

## Executive finding

The original M7 HumanEval hybrid runs contained a feedback-fidelity defect:
when a compound `check(candidate)` harness failed on an assertion other than
its first assertion, the generated feedback could cite the first assertion
rather than the assertion identified by the traceback. Correcting the defect
did not change adaptive aggregate accuracy, but it changed paired problem
outcomes. In fixed-k mode it reduced ever-solved accuracy by one problem and
final-iteration-only accuracy by two problems.

The corrected HumanEval figures in this document and their committed
per-problem artifacts are now the authoritative M7 HumanEval hybrid results.
They supersede the confounded adaptive and fixed-k artifacts introduced in
commits `ef2206f` and `a84a2ee`, respectively.

## 1. Discovery through cross-model coding consistency

The defect was discovered during the M7 error-taxonomy reliability work. A
12-case blinded sample was independently coded by Claude and compared with the
original Codex taxonomy coding. The resulting analysis was correctly framed as
**cross-model coding consistency (Codex vs. Claude)**, not human inter-rater
reliability.

Although category and mechanism agreement were perfect in that small sample,
manual review of the raw trajectories revealed that HumanEval/75,
HumanEval/127, and HumanEval/146 displayed feedback assertions different from
the assertions at the terminal traceback frames. Extending the check to the
full 50-case taxonomy confirmed nine affected HumanEval cases. This finding
was methodologically separate from the agreement calculation: both coders had
seen the same defective recorded feedback.

The investigation and taxonomy reconciliation are documented in
[`interrater_reliability_results.md`](interrater_reliability_results.md) and
[`error_taxonomy_correction_log.md`](error_taxonomy_correction_log.md).

## 2. Scope of the defect

The defect was specific to compound HumanEval harnesses. HumanEval problems
were stored as a single `check(candidate)` test containing multiple
assertions. When assertion instrumentation could not attach a single
`assertion_expression`, feedback generation fell back to the first textual
assertion in the compound test instead of recovering the assertion named by
the traceback.

MBPP was unaffected because its assertions had already been split into atomic
per-assertion test cases since M3.

This claim was also checked directly against every stored M5 MBPP development
refinement trajectory and both M7 MBPP full-scale refinement trajectories,
rather than inferred from the atomic-test structure alone. For each feedback
entry that cited a failed assertion, the cited expression was AST-normalized
and compared with the failed atomic assertion expressions in that iteration's
execution record.

| MBPP run | Matching cited assertions | Mismatched cited assertions | Clean feedback-bearing failed iterations |
|---|---:|---:|---:|
| M5 template, development set | 61 | 0 | 22/22 |
| M5 trace, development set | 65 | 0 | 25/25 |
| M5 hybrid, development set | 62 | 0 | 22/22 |
| M7 hybrid adaptive, full scale | 641 | 0 | 240/240 |
| M7 hybrid fixed-k=5, full scale | 1,037 | 0 | 397/397 |
| **Total** | **1,866** | **0** | **706/706** |

At the run-problem level, all 234 run-specific problems containing at least one
assertion citation were clean and zero were affected. Exception-oriented
feedback entries that cited no assertion were outside this assertion-identity
denominator; they cannot exhibit the specific defect under audit.

The audit of the original M7 hybrid runs found:

| Original run | Mismatched failed-feedback iterations | Affected problems |
|---|---:|---:|
| HumanEval hybrid adaptive | 37/54 (68.5%) | 17/25 |
| HumanEval hybrid fixed-k=5 | 89/127 (70.1%) | 22/31 |

Thus approximately 69–70% of failed-feedback iterations in the original M7
HumanEval hybrid runs cited the wrong assertion. This measures feedback
fidelity, not outcome impact: a mismatched assertion could expose the same
underlying defect, expose an irrelevant case, or alter the model response
through wording alone.

The M5 HumanEval development-set trace and hybrid runs were separately audited
and found unaffected. In particular, the HumanEval/83 trace regression was
clean and is not explained by this bug.

## 3. Fix and validation

Commit `89979b3` changed compound-harness failure handling to recover the
assertion at the traceback-identified source line. A regression test constructs
a compound harness whose failing assertion is not the first assertion and
verifies that feedback cites the actual failing assertion.

Both full HumanEval-164 hybrid configurations were then rerun from the frozen
protocol:

- corrected adaptive artifacts: commit `15dc62a`;
- corrected fixed-k=5 artifacts: commit `c10e59e`.

For both reruns, artifact identity and run integrity were checked, results were
persisted incrementally, and every first-iteration candidate was confirmed
identical to its counterpart in the confounded run. The corrected adaptive run
contained zero mismatches across 54 failed-feedback iterations; the corrected
fixed run contained zero mismatches across 130 failed-feedback iterations.

These are local Qwen2.5-Coder-7B `Q4_K_M` quantized-development measurements,
not the planned full-precision GPU dissertation results.

## 4. Confounded versus corrected results

`pass@1_refined` and fixed-k ever-solved both mean that a problem passed at
least once within five iterations. Final-only is a fixed-k diagnostic based
solely on iteration 5.

| Mode and metric | Confounded | Corrected | Absolute change |
|---|---:|---:|---:|
| Adaptive `pass@1_refined` | 143/164 = 0.8720 | **143/164 = 0.8720** | 0 problems (0.00 pp) |
| Adaptive model calls | 202 | **202** | 0 |
| Fixed-k=5 ever-solved | 144/164 = 0.8780 | **143/164 = 0.8720** | -1 problem (-0.61 pp) |
| Fixed-k=5 final-only | 140/164 = 0.8537 | **138/164 = 0.8415** | -2 problems (-1.22 pp) |
| Fixed-k=5 model calls | 820 | **820** | 0 |

The adaptive aggregate was unchanged, but the invariant aggregate conceals a
real paired effect. The fixed-k correction produced a small negative aggregate
change. Therefore, the bug did not overturn the broad M7 HumanEval conclusion,
but the original aggregate values alone were insufficient to characterize its
impact.

## 5. Paired outcome changes

### Adaptive

Two of the 17 previously affected problems flipped in opposite directions:

| Problem | Confounded | Corrected |
|---|---|---|
| HumanEval/91 | Failed | Passed |
| HumanEval/115 | Passed | Failed |

This is a zero-net paired effect: one gain and one loss.

### Fixed-k=5

For the protocol metric, HumanEval/115 changed from ever solved to never
solved, with no compensating ever-solved gain:

| Problem | Metric | Confounded | Corrected |
|---|---|---|---|
| HumanEval/115 | Ever-solved | Passed | Failed |

Among the 22 previously affected problems, three final-only outcomes changed:

| Problem | Metric | Confounded | Corrected |
|---|---|---|---|
| HumanEval/126 | Final-only | Failed | Passed |
| HumanEval/134 | Final-only | Passed | Failed |
| HumanEval/138 | Final-only | Passed | Failed |

These changes yield one gain and two losses within the affected set.

HumanEval/100 also changed from final-pass to final-fail, despite being outside
the original 22-problem assertion-identity mismatch set. Its feedback referred
to the same substantive failing assertion, but the corrected extraction path
changed semantically equivalent wording and formatting. Subsequent candidates
then diverged. This is direct evidence that the refinement trajectory is
sensitive to prompt phrasing even at temperature 0.2 with a fixed seed.

That observation should not be interpreted as a failure of seed control:
fixed seeds make a run reproducible for a fixed prompt and software state, but
they do not guarantee invariant generations after the prompt text changes.

## 6. Authoritative M7 HumanEval figures

For all subsequent M7 analysis, tables, dissertation prose, and comparisons,
use:

- hybrid adaptive `pass@1_refined`: **143/164 = 0.8720**, 202 calls;
- hybrid fixed-k=5 ever-solved: **143/164 = 0.8720**, 820 calls;
- hybrid fixed-k=5 final-only: **138/164 = 0.8415**.

The earlier HumanEval hybrid figures from commits `ef2206f` and `a84a2ee`
remain preserved as provenance for the confounded runs, but they are
superseded for reporting. The implementation correction is `89979b3`; the
authoritative corrected run evidence is tracked by `15dc62a` and `c10e59e`.
