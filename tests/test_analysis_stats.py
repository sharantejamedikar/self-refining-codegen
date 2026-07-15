"""Math-focused tests for paired binary statistical analysis."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path

import pytest

from analysis.report import analyze_plan, load_analysis_plan
from analysis.results import load_paired_outcomes, load_pass_fail_vector
from analysis.stats import bootstrap_pass_at_1, mcnemar_exact


def test_mcnemar_exact_known_discordant_table() -> None:
    """Match the hand-computable exact binomial result for b=10, c=2."""

    first = [True] * 10 + [False] * 2
    second = [False] * 10 + [True] * 2
    result = mcnemar_exact(first, second)

    assert result.first_only == 10
    assert result.second_only == 2
    assert result.discordant_pairs == 12
    assert result.p_value == pytest.approx(158 / 4096)
    assert result.paired_risk_difference == pytest.approx(8 / 12)
    assert result.matched_odds_ratio == pytest.approx(5.0)
    assert not result.odds_ratio_zero_cell_correction
    assert result.method == "exact_conditional_binomial_two_sided"
    assert not result.continuity_correction


def test_mcnemar_zero_cell_effect_size_is_finite_and_flagged() -> None:
    first = [True] * 4 + [True] * 3 + [False] * 3
    second = [False] * 4 + [True] * 3 + [False] * 3
    result = mcnemar_exact(first, second)

    assert result.p_value == pytest.approx(0.125)
    assert result.unadjusted_matched_odds_ratio is None
    assert result.matched_odds_ratio == pytest.approx(9.0)
    assert result.odds_ratio_zero_cell_correction
    assert result.paired_risk_difference == pytest.approx(0.4)


def test_mcnemar_is_symmetric_except_directional_effects() -> None:
    first = [True, True, True, False, False, True]
    second = [False, False, True, True, False, True]
    forward = mcnemar_exact(first, second)
    reverse = mcnemar_exact(second, first)

    assert forward.p_value == reverse.p_value
    assert forward.matched_odds_ratio == pytest.approx(1 / reverse.matched_odds_ratio)
    assert forward.paired_risk_difference == pytest.approx(
        -reverse.paired_risk_difference
    )


def test_mcnemar_all_concordant_has_no_evidence_of_difference() -> None:
    result = mcnemar_exact([True, False, True], [True, False, True])

    assert result.discordant_pairs == 0
    assert result.p_value == 1.0
    assert result.paired_risk_difference == 0.0
    assert result.matched_odds_ratio == 1.0
    assert result.odds_ratio_zero_cell_correction


def test_bootstrap_pass_at_1_degenerate_and_reproducible() -> None:
    perfect = bootstrap_pass_at_1([True] * 8, resamples=500, seed=7)
    assert perfect.estimate == perfect.lower == perfect.upper == 1.0

    outcomes = [True, False, True, False]
    first = bootstrap_pass_at_1(outcomes, resamples=1_000, seed=123)
    second = bootstrap_pass_at_1(outcomes, resamples=1_000, seed=123)
    assert first == second
    assert first.estimate == 0.5
    assert first.lower == 0.0
    assert first.upper == 1.0
    assert first.confidence_level == 0.95


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: mcnemar_exact([], []), "non-empty"),
        (lambda: mcnemar_exact([True], [True, False]), "same length"),
        (lambda: mcnemar_exact([1], [True]), "bool"),
        (lambda: bootstrap_pass_at_1([], seed=1), "non-empty"),
        (
            lambda: bootstrap_pass_at_1([True], resamples=0, seed=1),
            "resamples",
        ),
        (
            lambda: bootstrap_pass_at_1([True], confidence_level=1.0, seed=1),
            "confidence_level",
        ),
    ],
)
def test_statistical_input_validation(call: Callable[[], object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        call()


def _write_record(directory: Path, task_id: str, passed: bool) -> None:
    problem_dir = directory / "problems"
    problem_dir.mkdir(parents=True, exist_ok=True)
    filename = task_id.replace("/", "_") + ".json"
    (problem_dir / filename).write_text(
        json.dumps({"task_id": task_id, "passed": passed}), encoding="utf-8"
    )


def test_result_loader_pairs_by_task_id_not_filename_order(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_record(first, "Fixture/2", False)
    _write_record(first, "Fixture/1", True)
    _write_record(second, "Fixture/1", False)
    _write_record(second, "Fixture/2", True)

    task_ids, first_outcomes, second_outcomes = load_paired_outcomes(first, second)
    assert task_ids == ("Fixture/1", "Fixture/2")
    assert first_outcomes == (True, False)
    assert second_outcomes == (False, True)


def test_result_loader_rejects_malformed_and_unpaired_runs(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_record(first, "Fixture/1", True)
    _write_record(second, "Fixture/2", False)
    with pytest.raises(ValueError, match="task IDs differ"):
        load_paired_outcomes(first, second)

    malformed = tmp_path / "malformed"
    _write_record(malformed, "Fixture/1", True)
    path = malformed / "problems" / "Fixture_1.json"
    path.write_text(json.dumps({"task_id": "Fixture/1", "passed": 1}))
    with pytest.raises(ValueError, match="boolean 'passed'"):
        load_pass_fail_vector(malformed)


def test_effect_size_with_zero_denominator_is_not_infinite() -> None:
    result = mcnemar_exact([True, True], [False, False])
    assert math.isfinite(result.matched_odds_ratio)


def test_typed_analysis_plan_runs_entirely_from_synthetic_json(
    tmp_path: Path,
) -> None:
    _write_record(tmp_path / "first", "Fixture/1", True)
    _write_record(tmp_path / "first", "Fixture/2", False)
    _write_record(tmp_path / "second", "Fixture/1", False)
    _write_record(tmp_path / "second", "Fixture/2", False)
    config = tmp_path / "analysis.yaml"
    config.write_text(
        """
analysis:
  seed: 9
  bootstrap_resamples: 100
  confidence_level: 0.95
  significance_level: 0.05
  output_path: report.json
runs:
  first:
    label: First
    benchmark: Fixture
    run_dir: first
  second:
    label: Second
    benchmark: Fixture
    run_dir: second
comparisons:
  - key: first_vs_second
    first: first
    second: second
""".strip(),
        encoding="utf-8",
    )

    plan = load_analysis_plan(config)
    report = analyze_plan(plan, tmp_path)
    assert report["methodology"]["bootstrap_resamples"] == 100
    assert report["configurations"]["first"]["pass@1"] == 0.5
    comparison = report["comparisons"]["first_vs_second"]
    assert comparison["mcnemar"]["first_only"] == 1
    assert comparison["mcnemar"]["p_value"] == 1.0
    assert not comparison["significant"]


def test_analysis_plan_rejects_unknown_comparison_run(tmp_path: Path) -> None:
    config = tmp_path / "analysis.yaml"
    config.write_text(
        """
analysis:
  seed: 9
  bootstrap_resamples: 100
  confidence_level: 0.95
  significance_level: 0.05
  output_path: report.json
runs:
  first:
    label: First
    benchmark: Fixture
    run_dir: first
comparisons:
  - key: invalid
    first: first
    second: missing
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown runs"):
        load_analysis_plan(config)
