"""Load and align persisted per-problem pass/fail experiment records."""

from __future__ import annotations

import json
from pathlib import Path


def load_pass_fail_vector(run_dir: str | Path) -> dict[str, bool]:
    """Return ``task_id -> passed`` from one committed experiment run."""

    directory = Path(run_dir)
    problem_dir = directory / "problems"
    paths = sorted(problem_dir.glob("*.json"))
    if not paths:
        raise ValueError(f"No per-problem JSON files found in {problem_dir}")

    outcomes: dict[str, bool] = {}
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot load result record {path}: {error}") from error
        if not isinstance(record, dict):
            raise ValueError(f"Result record must be an object: {path}")
        task_id = record.get("task_id")
        passed = record.get("passed")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(f"Result record needs a non-empty string task_id: {path}")
        if type(passed) is not bool:
            raise ValueError(f"Result record needs a boolean 'passed' field: {path}")
        if task_id in outcomes:
            raise ValueError(f"Duplicate task_id {task_id!r} in {problem_dir}")
        outcomes[task_id] = passed
    return outcomes


def load_paired_outcomes(
    first_run_dir: str | Path, second_run_dir: str | Path
) -> tuple[tuple[str, ...], tuple[bool, ...], tuple[bool, ...]]:
    """Align two run outcome vectors by exact task ID and return sorted pairs."""

    first = load_pass_fail_vector(first_run_dir)
    second = load_pass_fail_vector(second_run_dir)
    first_ids = set(first)
    second_ids = set(second)
    if first_ids != second_ids:
        first_only = sorted(first_ids - second_ids)
        second_only = sorted(second_ids - first_ids)
        raise ValueError(
            "paired run task IDs differ; "
            f"first-only={first_only}, second-only={second_only}"
        )
    task_ids = tuple(sorted(first_ids))
    return (
        task_ids,
        tuple(first[task_id] for task_id in task_ids),
        tuple(second[task_id] for task_id in task_ids),
    )
