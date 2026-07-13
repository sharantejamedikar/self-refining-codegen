# MBPP prompt-contract correction

**Date diagnosed:** 2026-07-14  
**Fix commit:** `bdbe26f912d367584056c43551e68ddf6f07d5ab`

## Cause

The sanitized MBPP release does not provide a dedicated entry-point field. Its
natural-language `prompt` often omits the required function name, although that
name remains available in both the reference `code` and calls in `test_list`.
The original normalization retained those fields as `canonical_solution` and
`test_cases` but copied only the underspecified natural-language text into the
generation prompt. Consequently, the model could implement the requested
behaviour under a plausible but untested function name.

## Detection and impact

The issue was found during the diagnostic review of the first M4 MBPP-Dev runs,
before their results were accepted. Single-pass failed on 47 of 50 problems; in
45 of those 47 failures, the generated program defined none of the canonical
tested entry-point names. All 45 were correctly classified as `runtime`, not
`logic`: each test raised `NameError` when it called the missing function. The
implausibly low initial scores (`3/50` single-pass, `4/50` best-of-5, and `3/50`
refinement) therefore measured a broken prompt contract rather than meaningful
code-generation performance.

The following local Q4_K_M development runs are retained for auditability but
are **invalid and superseded**:

- [Invalid single-pass run](../../experiments/results/20260713T194903.209391Z_m2_qwen_ollama_zero_shot_mbpp_dev/)
- [Invalid best-of-5 run](../../experiments/results/20260713T195031.048111Z_m4_qwen_ollama_best_of_5_mbpp_dev/)
- [Invalid refinement run](../../experiments/results/20260713T195902.932791Z_m3_qwen_ollama_template_refinement_mbpp_dev/)

## Fix and authoritative development runs

MBPP normalization now parses the reference solution and assertions with
`ast`, intersects top-level functions defined in `code` with functions called
by the tests, and appends the resulting exact signature to the generation
prompt. Normalization fails loudly unless exactly one tested top-level function
is found. An audit of all 427 sanitized records found exactly one such function
for every record. Regression tests require a normalized MBPP prompt to contain
the extracted signature and cover the missing-entry-point failure case.

The frozen 50-problem MBPP-Dev split was regenerated without resampling; only
the prompt field changed, and all 50 canonical solutions passed sandboxed
validation. The following `bdbe26f` local Q4_K_M runs are the **authoritative M4
MBPP-Dev development artifacts**:

- [Authoritative single-pass run](../../experiments/results/20260713T200916.764652Z_m2_qwen_ollama_zero_shot_mbpp_dev/) — `38/50`
- [Authoritative best-of-5 run](../../experiments/results/20260713T201055.926372Z_m4_qwen_ollama_best_of_5_mbpp_dev/) — `40/50`
- [Authoritative refinement run](../../experiments/results/20260713T201936.683659Z_m3_qwen_ollama_template_refinement_mbpp_dev/) — `39/50`

These quantized MacBook runs support development and methodological validation
only. Dissertation-reported benchmark numbers must come from the planned
full-precision GPU runs.

## Complementary-failure case studies

MBPP/446 was a clean refinement-only success: its first solution returned a
frequency dictionary instead of the required total, failed `0/3` tests, and was
classified as `logic`; feedback showed each dictionary beside the expected
integer and advised reconsidering the core algorithm, after which one
regeneration summed the counts and passed `3/3`, while all five best-of-5
samples retained the same return-shape misconception. MBPP/597 was a `runtime`
failure: the recursive kth-element algorithm raised `RecursionError`, feedback
reported only "maximum recursion depth exceeded," and refinement regenerated
identical code, triggering oscillation at iteration 2; best-of-5 instead
sampled valid partition-based algorithms at seeds 43, 44, and 46. MBPP/734 was
messier: the initial sum-not-product algorithm passed `1/3` and was classified
as `edge_case`; feedback supplied both failing actual/expected pairs, but the
next solution changed to another incorrect weighted-sum method, regressed to
`0/3` (`logic`), repeated unchanged, and stopped by oscillation at iteration 3.
Best-of-5 solved it only at seed 45 by sampling the correct contiguous-subarray
product loop. Together, these cases show refinement working well for an
explicit output-shape error, but struggling when generic runtime feedback or
misleading partial correctness does not expose the underlying algorithmic
misconception.

The MBPP/734 convergence record confirms that the `1/3` to `0/3` regression was
not mistaken for stagnation: iteration 2 had a new pass rate, code hash, and
error hash and therefore returned `continue`. Iteration 3 exactly repeated
iteration 2's code hash (`fa3cd4...`) and error hash (`cca748...`), so the final
`oscillation` decision was a genuine code repeat.
