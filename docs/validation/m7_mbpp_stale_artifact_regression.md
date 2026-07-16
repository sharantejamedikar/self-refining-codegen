# M7 MBPP stale-artifact regression

**Date diagnosed:** 2026-07-16  
**Guard commit:** `77f91a713db0322526420d4bfaa9a2cf55eadf92`  
**Corrected-result commit:** `a0f16cc25ccad8e05a7420c59d1abd30b411c0ae`

## Cause

The M7 full-set MBPP configs pointed to
`data/normalized/mbpp_sanitized.jsonl`, which had been generated on July 13
before the prompt-contract fix in `bdbe26f`. The 427-record artifact was never
regenerated after that fix, so every prompt still lacked the exact tested
function signature even though `src/data/loaders.py` contained the corrected
normalization logic. M4 and M5 did not exhibit the regression because their
regenerated MBPP-Dev artifact contained the required signatures.

## Detection and invalid run

The first M7 full MBPP single-pass run scored `31/427` (`7.26%`), drastically
below the `38/50` (`76%`) MBPP-Dev baseline. That discrepancy triggered an
investigation before the full-set result was trusted. Inspection confirmed
that all 427 rendered prompts lacked the required-signature block; the run
therefore measured the previously identified broken prompt contract, not model
performance.

The invalid run directory
`experiments/results/20260716T163337.901412Z_m7_quantized_local_development_single_mbpp_full/`
is preserved on disk for auditability, but is untracked and excluded from Git.
It is invalid, superseded, and **must never be used analytically**.

## Fix and corrected result

The full normalized MBPP artifact was regenerated from the raw sanitized
source, producing 427 unique task IDs and 427 exact tested-signature blocks.
In addition, `load_jsonl()` now recomputes the tested entry-point signature
from each normalized MBPP record's canonical solution and tests, and fails
before generation unless the prompt contains exactly one matching signature
block. Regression tests cover rejection of the stale format and acceptance of
the corrected format.

The corrected local Q4_K_M single-pass run scored `311/427` (`72.83%`), which
is consistent with the `76%` MBPP-Dev baseline. Its committed results are the
authoritative M7 quantized-local MBPP single-pass development artifact:

- [Corrected full MBPP single-pass run](../../experiments/results/20260716T171911.599683Z_m7_quantized_local_development_single_mbpp_full/)

As with the other local Q4_K_M runs, this result supports development and
methodological validation only; dissertation-reported numbers must come from
the planned full-precision GPU runs.
