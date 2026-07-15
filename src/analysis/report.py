"""Typed, config-driven statistical reports over committed experiment runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from analysis.results import load_paired_outcomes, load_pass_fail_vector
from analysis.stats import bootstrap_pass_at_1, mcnemar_exact


@dataclass(frozen=True)
class RunSpec:
    """One named experiment run included in an analysis report."""

    key: str
    label: str
    benchmark: str
    run_dir: str


@dataclass(frozen=True)
class ComparisonSpec:
    """One directional paired comparison: first configuration versus second."""

    key: str
    first: str
    second: str


@dataclass(frozen=True)
class AnalysisPlan:
    """Complete reproducible specification for an offline statistical report."""

    seed: int
    bootstrap_resamples: int
    confidence_level: float
    significance_level: float
    output_path: str
    runs: tuple[RunSpec, ...]
    comparisons: tuple[ComparisonSpec, ...]


def load_analysis_plan(path: str | Path) -> AnalysisPlan:
    """Load a typed analysis plan from YAML and validate all references."""

    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("analysis configuration root must be a mapping")
    allowed = {"analysis", "runs", "comparisons"}
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"Unknown analysis configuration sections: {sorted(unknown)}")

    settings = raw.get("analysis")
    raw_runs = raw.get("runs")
    raw_comparisons = raw.get("comparisons")
    if not isinstance(settings, dict):
        raise ValueError("analysis section must be a mapping")
    if not isinstance(raw_runs, dict) or not raw_runs:
        raise ValueError("runs section must be a non-empty mapping")
    if not isinstance(raw_comparisons, list) or not raw_comparisons:
        raise ValueError("comparisons section must be a non-empty list")

    setting_keys = {
        "seed",
        "bootstrap_resamples",
        "confidence_level",
        "significance_level",
        "output_path",
    }
    unknown_settings = set(settings) - setting_keys
    if unknown_settings:
        raise ValueError(f"Unknown analysis settings: {sorted(unknown_settings)}")
    missing_settings = setting_keys - set(settings)
    if missing_settings:
        raise ValueError(f"Missing analysis settings: {sorted(missing_settings)}")

    runs: list[RunSpec] = []
    for key, values in raw_runs.items():
        if not isinstance(key, str) or not isinstance(values, dict):
            raise ValueError("each run must be a named mapping")
        expected = {"label", "benchmark", "run_dir"}
        if set(values) != expected:
            raise ValueError(f"run {key!r} must contain exactly {sorted(expected)}")
        runs.append(
            RunSpec(
                key=key,
                label=_non_empty_string(values["label"], f"run {key} label"),
                benchmark=_non_empty_string(
                    values["benchmark"], f"run {key} benchmark"
                ),
                run_dir=_non_empty_string(values["run_dir"], f"run {key} run_dir"),
            )
        )

    comparisons: list[ComparisonSpec] = []
    for index, values in enumerate(raw_comparisons):
        if not isinstance(values, dict) or set(values) != {"key", "first", "second"}:
            raise ValueError(
                f"comparison {index} must contain exactly key, first, and second"
            )
        comparisons.append(
            ComparisonSpec(
                key=_non_empty_string(values["key"], f"comparison {index} key"),
                first=_non_empty_string(values["first"], f"comparison {index} first"),
                second=_non_empty_string(
                    values["second"], f"comparison {index} second"
                ),
            )
        )

    run_keys = {run.key for run in runs}
    if len(run_keys) != len(runs):
        raise ValueError("run keys must be unique")
    comparison_keys = {comparison.key for comparison in comparisons}
    if len(comparison_keys) != len(comparisons):
        raise ValueError("comparison keys must be unique")
    for comparison in comparisons:
        missing = {comparison.first, comparison.second} - run_keys
        if missing:
            raise ValueError(
                f"comparison {comparison.key!r} references unknown runs: "
                f"{sorted(missing)}"
            )

    plan = AnalysisPlan(
        seed=int(settings["seed"]),
        bootstrap_resamples=int(settings["bootstrap_resamples"]),
        confidence_level=float(settings["confidence_level"]),
        significance_level=float(settings["significance_level"]),
        output_path=_non_empty_string(settings["output_path"], "analysis output_path"),
        runs=tuple(runs),
        comparisons=tuple(comparisons),
    )
    _validate_plan(plan)
    return plan


def analyze_plan(
    plan: AnalysisPlan, repository_root: str | Path = "."
) -> dict[str, Any]:
    """Compute bootstrap intervals and exact paired comparisons from JSON only."""

    _validate_plan(plan)
    root = Path(repository_root)
    run_by_key = {run.key: run for run in plan.runs}
    outcomes: dict[str, dict[str, bool]] = {}
    configuration_results: dict[str, dict[str, Any]] = {}
    for run in plan.runs:
        run_path = root / run.run_dir
        vector = load_pass_fail_vector(run_path)
        outcomes[run.key] = vector
        interval = bootstrap_pass_at_1(
            tuple(vector[task_id] for task_id in sorted(vector)),
            resamples=plan.bootstrap_resamples,
            confidence_level=plan.confidence_level,
            seed=plan.seed,
        )
        configuration_results[run.key] = {
            "label": run.label,
            "benchmark": run.benchmark,
            "run_dir": run.run_dir,
            "sample_size": len(vector),
            "solved": sum(vector.values()),
            "pass@1": interval.estimate,
            "bootstrap_ci": interval.to_dict(),
        }

    comparison_results: dict[str, dict[str, Any]] = {}
    for comparison in plan.comparisons:
        first_spec = run_by_key[comparison.first]
        second_spec = run_by_key[comparison.second]
        if first_spec.benchmark != second_spec.benchmark:
            raise ValueError(
                f"comparison {comparison.key!r} crosses benchmarks: "
                f"{first_spec.benchmark!r} and {second_spec.benchmark!r}"
            )
        task_ids, first, second = load_paired_outcomes(
            root / first_spec.run_dir, root / second_spec.run_dir
        )
        result = mcnemar_exact(first, second)
        comparison_results[comparison.key] = {
            "benchmark": first_spec.benchmark,
            "first": comparison.first,
            "first_label": first_spec.label,
            "second": comparison.second,
            "second_label": second_spec.label,
            "paired_task_ids": list(task_ids),
            "mcnemar": result.to_dict(),
            "significance_level": plan.significance_level,
            "significant": result.p_value < plan.significance_level,
        }

    return {
        "methodology": {
            "mcnemar": "exact conditional two-sided binomial; no continuity correction",
            "bootstrap": "problem-level nonparametric percentile bootstrap",
            "bootstrap_resamples": plan.bootstrap_resamples,
            "confidence_level": plan.confidence_level,
            "seed": plan.seed,
            "effect_sizes": [
                "paired risk difference (first - second)",
                "matched-pairs odds ratio (first-only / second-only)",
                "Haldane-Anscombe +0.5 correction only for zero discordant cells",
            ],
            "multiplicity_correction": None,
        },
        "configurations": configuration_results,
        "comparisons": comparison_results,
    }


def _validate_plan(plan: AnalysisPlan) -> None:
    if plan.bootstrap_resamples <= 0:
        raise ValueError("bootstrap_resamples must be positive")
    if not 0.0 < plan.confidence_level < 1.0:
        raise ValueError("confidence_level must be strictly between 0 and 1")
    if not 0.0 < plan.significance_level < 1.0:
        raise ValueError("significance_level must be strictly between 0 and 1")
    if not plan.runs:
        raise ValueError("analysis plan needs at least one run")
    if not plan.comparisons:
        raise ValueError("analysis plan needs at least one comparison")


def _non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value
