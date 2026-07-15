"""Dependency-free statistics for paired binary code-generation outcomes."""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BootstrapInterval:
    """Percentile bootstrap confidence interval for a pass@1 proportion."""

    estimate: float
    lower: float
    upper: float
    confidence_level: float
    resamples: int
    seed: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


@dataclass(frozen=True)
class McNemarResult:
    """Exact paired comparison and directional binary effect sizes."""

    sample_size: int
    both_pass: int
    first_only: int
    second_only: int
    both_fail: int
    discordant_pairs: int
    first_pass_rate: float
    second_pass_rate: float
    paired_risk_difference: float
    unadjusted_matched_odds_ratio: float | None
    matched_odds_ratio: float
    odds_ratio_zero_cell_correction: bool
    p_value: float
    method: str = "exact_conditional_binomial_two_sided"
    continuity_correction: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


def mcnemar_exact(
    first: list[bool] | tuple[bool, ...],
    second: list[bool] | tuple[bool, ...],
) -> McNemarResult:
    """Compare paired outcomes with the exact two-sided McNemar test.

    The null conditions on the number of discordant pairs and assigns either
    direction probability 0.5. No continuity correction is used because this
    is the exact conditional binomial test, not a chi-square approximation.
    Directional effects are ``first - second``.
    """

    first_values = _validated_outcomes(first, "first")
    second_values = _validated_outcomes(second, "second")
    if len(first_values) != len(second_values):
        raise ValueError("paired outcome vectors must have the same length")

    both_pass = sum(a and b for a, b in zip(first_values, second_values, strict=True))
    first_only = sum(
        a and not b for a, b in zip(first_values, second_values, strict=True)
    )
    second_only = sum(
        not a and b for a, b in zip(first_values, second_values, strict=True)
    )
    both_fail = len(first_values) - both_pass - first_only - second_only
    discordant = first_only + second_only
    p_value = _exact_binomial_two_sided(first_only, second_only)

    zero_cell_correction = first_only == 0 or second_only == 0
    if zero_cell_correction:
        matched_odds_ratio = (first_only + 0.5) / (second_only + 0.5)
    else:
        matched_odds_ratio = first_only / second_only
    unadjusted = None if second_only == 0 else first_only / second_only
    sample_size = len(first_values)
    first_rate = (both_pass + first_only) / sample_size
    second_rate = (both_pass + second_only) / sample_size
    return McNemarResult(
        sample_size=sample_size,
        both_pass=both_pass,
        first_only=first_only,
        second_only=second_only,
        both_fail=both_fail,
        discordant_pairs=discordant,
        first_pass_rate=first_rate,
        second_pass_rate=second_rate,
        paired_risk_difference=first_rate - second_rate,
        unadjusted_matched_odds_ratio=unadjusted,
        matched_odds_ratio=matched_odds_ratio,
        odds_ratio_zero_cell_correction=zero_cell_correction,
        p_value=p_value,
    )


def bootstrap_pass_at_1(
    outcomes: list[bool] | tuple[bool, ...],
    *,
    resamples: int = 10_000,
    confidence_level: float = 0.95,
    seed: int,
) -> BootstrapInterval:
    """Estimate a problem-level percentile bootstrap CI for pass@1.

    Each replicate samples ``n`` problem outcomes with replacement from the
    observed vector and recomputes the solved fraction. Quantiles use linear
    interpolation between adjacent ordered replicates (the common type-7
    definition).
    """

    values = _validated_outcomes(outcomes, "outcomes")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be strictly between 0 and 1")

    rng = random.Random(seed)
    sample_size = len(values)
    estimates = sorted(
        sum(rng.choice(values) for _ in range(sample_size)) / sample_size
        for _ in range(resamples)
    )
    alpha = 1.0 - confidence_level
    return BootstrapInterval(
        estimate=sum(values) / sample_size,
        lower=_quantile(estimates, alpha / 2.0),
        upper=_quantile(estimates, 1.0 - alpha / 2.0),
        confidence_level=confidence_level,
        resamples=resamples,
        seed=seed,
    )


def _validated_outcomes(
    outcomes: list[bool] | tuple[bool, ...], name: str
) -> tuple[bool, ...]:
    values = tuple(outcomes)
    if not values:
        raise ValueError(f"{name} outcome vector must be non-empty")
    if any(type(value) is not bool for value in values):
        raise ValueError(f"{name} outcomes must contain only bool values")
    return values


def _exact_binomial_two_sided(first_only: int, second_only: int) -> float:
    discordant = first_only + second_only
    if discordant == 0:
        return 1.0
    smaller = min(first_only, second_only)
    lower_tail = sum(math.comb(discordant, value) for value in range(smaller + 1))
    return min(1.0, 2.0 * lower_tail / (2**discordant))


def _quantile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = position - lower_index
    return (
        sorted_values[lower_index] * (1.0 - weight)
        + sorted_values[upper_index] * weight
    )
