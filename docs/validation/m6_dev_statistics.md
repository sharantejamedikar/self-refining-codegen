# M6 offline statistical worked example

**Date:** 2026-07-15  
**Scope:** committed HumanEval-Dev and corrected MBPP-Dev M4/M5 runs  
**Source:** per-problem JSON only; no model calls or experiment reruns

The machine-readable output is in `m6_dev_statistics.json`, generated with:

```bash
PYTHONPATH=src .venv/bin/python experiments/scripts/analyze_statistics.py \
  --config configs/m6_dev_statistics.yaml
```

These are local Qwen `Q4_K_M` development measurements, not dissertation-reported
full-precision GPU results.

## Methodology

- **Paired comparison:** exact two-sided conditional-binomial McNemar test. It
  conditions on the discordant pairs and tests whether either direction has
  probability 0.5. No continuity correction is applied because this is the exact
  test, not the asymptotic chi-square approximation.
- **Uncertainty for pass@1:** nonparametric percentile bootstrap over problems,
  sampling `n` problem outcomes with replacement for each of 10,000 replicates.
  The interval uses the 2.5th and 97.5th percentiles with seed 42.
- **Effect sizes:** paired risk difference (`first - second`) and the matched-pairs
  odds ratio (`first-only / second-only`). When either discordant cell is zero, the
  odds ratio uses a disclosed Haldane–Anscombe `+0.5` correction rather than
  reporting an infinite or undefined value.
- All p-values below are unadjusted. No multiplicity correction was applied to this
  exploratory dev-set worked example.

## Bootstrap 95% confidence intervals

| Benchmark | Configuration | pass@1 | Bootstrap 95% CI |
|---|---|---:|---:|
| HumanEval-Dev | Single pass | 0.85 | [0.70, 1.00] |
| HumanEval-Dev | Template refinement | 0.95 | [0.85, 1.00] |
| HumanEval-Dev | Best of 5 | 0.95 | [0.85, 1.00] |
| HumanEval-Dev | Trace feedback | 0.90 | [0.75, 1.00] |
| HumanEval-Dev | Hybrid feedback | 0.90 | [0.75, 1.00] |
| MBPP-Dev | Single pass | 0.76 | [0.64, 0.88] |
| MBPP-Dev | Template refinement | 0.78 | [0.66, 0.88] |
| MBPP-Dev | Best of 5 | 0.80 | [0.68, 0.90] |
| MBPP-Dev | Trace feedback | 0.84 | [0.74, 0.94] |
| MBPP-Dev | Hybrid feedback | 0.84 | [0.74, 0.94] |

The wide intervals are expected with only 20 and 50 problems. Interval overlap is
descriptive here; the paired McNemar result, not CI overlap, is the formal comparison.

## Paired comparisons

The directional columns count problems solved only by the first configuration and
only by the second configuration.

| Benchmark | First vs second | First-only | Second-only | Risk difference | Matched OR | Exact p | Significant at 0.05? |
|---|---|---:|---:|---:|---:|---:|---|
| HumanEval-Dev | Refinement vs best of 5 | 1 | 1 | 0.00 | 1.00 | 1.00 | No |
| MBPP-Dev | Refinement vs best of 5 | 1 | 2 | -0.02 | 0.50 | 1.00 | No |
| HumanEval-Dev | Trace vs template | 0 | 1 | -0.05 | 0.33 corrected | 1.00 | No |
| HumanEval-Dev | Hybrid vs template | 0 | 1 | -0.05 | 0.33 corrected | 1.00 | No |
| MBPP-Dev | Trace vs template | 3 | 0 | +0.06 | 7.00 corrected | 0.25 | No |
| MBPP-Dev | Hybrid vs template | 3 | 0 | +0.06 | 7.00 corrected | 0.25 | No |

## Interpretation

Neither headline refinement-versus-best-of-five difference is statistically
significant on the dev sets. HumanEval has equal aggregate accuracy but two opposing
discordant cases. MBPP differs by one net solve, with only three discordant cases;
the exact two-sided p-value is 1.00. The samples therefore provide very little power
to distinguish these already-close configurations.

The M5 cross-benchmark trade-off remains a real observed development result, but it
is not statistically established as a population-level effect here. HumanEval's loss
is one discordant problem (`p=1.00`), while MBPP's three one-directional gains yield
`p=0.25`. This is precisely why final claims require the planned full benchmark runs:
the dev sets are useful for engineering decisions and case analysis, not strong
inferential conclusions.
