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
