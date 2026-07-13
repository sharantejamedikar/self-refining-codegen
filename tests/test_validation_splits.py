"""Tests for canonical validation, quarantine, and dev splitting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data.schema import Problem
from data.splits import create_stratified_dev_split
from data.validation import validate_problems
from execution import SubprocessExecutor


def _problem(
    index: int, code: str = "x = 1", difficulty: str = "unspecified"
) -> Problem:
    return Problem(
        task_id=f"Fixture/{index}",
        prompt=f"problem {index}",
        canonical_solution=code,
        test_cases=("assert x == 1",),
        difficulty=difficulty,
        tags=("fixture",),
    )


def test_validation_quarantines_syntax_and_execution_failures(tmp_path: Path) -> None:
    problems = [_problem(1), _problem(2, "x = 2"), _problem(3, "def broken(:")]
    quarantine = tmp_path / "quarantine.jsonl"
    summary = validate_problems(
        problems,
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        quarantine,
    )
    assert [problem.task_id for problem in summary.valid] == ["Fixture/1"]
    assert len(summary.quarantined) == 2
    records = [json.loads(line) for line in quarantine.read_text().splitlines()]
    assert {record["failure"]["stage"] for record in records} == {"syntax", "execution"}


def test_quartile_split_is_seeded_stratified_and_naturally_sorted(
    tmp_path: Path,
) -> None:
    problems = [_problem(index) for index in range(1, 21)]
    first = create_stratified_dev_split(problems, 8, 99, tmp_path / "first.jsonl")
    second = create_stratified_dev_split(problems, 8, 99, tmp_path / "second.jsonl")
    assert first == second
    assert [int(problem.task_id.split("/")[-1]) for problem in first] == sorted(
        int(problem.task_id.split("/")[-1]) for problem in first
    )
    metadata = json.loads((tmp_path / "first.jsonl.meta.json").read_text())
    assert metadata["seed"] == 99
    assert metadata["strata_selected"] == {
        "task_id_quartile_1": 2,
        "task_id_quartile_2": 2,
        "task_id_quartile_3": 2,
        "task_id_quartile_4": 2,
    }


def test_split_uses_semantic_strata_and_rejects_bad_size(tmp_path: Path) -> None:
    problems = [
        _problem(index, difficulty="easy" if index < 5 else "hard")
        for index in range(8)
    ]
    selected = create_stratified_dev_split(problems, 4, 3, tmp_path / "semantic.jsonl")
    assert {problem.difficulty for problem in selected} == {"easy", "hard"}
    with pytest.raises(ValueError, match="size"):
        create_stratified_dev_split(problems, 0, 3, tmp_path / "bad.jsonl")
