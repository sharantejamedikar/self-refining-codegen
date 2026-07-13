"""Deterministic syntax and sandboxed canonical-solution validation."""

from __future__ import annotations

import ast
import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from data.schema import Problem
from execution.base import Executor

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationSummary:
    """Validated and quarantined benchmark partitions."""

    valid: tuple[Problem, ...]
    quarantined: tuple[Problem, ...]


def validate_problems(
    problems: Iterable[Problem], executor: Executor, quarantine_path: str | Path
) -> ValidationSummary:
    """Validate syntax and canonical tests, logging every quarantined problem."""

    valid: list[Problem] = []
    quarantined: list[Problem] = []
    records: list[dict[str, object]] = []
    for problem in problems:
        reason: dict[str, object] | None = None
        try:
            ast.parse(problem.canonical_solution)
        except SyntaxError as error:
            reason = {
                "stage": "syntax",
                "exception_type": type(error).__name__,
                "exception_message": str(error),
            }
        if reason is None:
            result = executor.execute(
                problem.canonical_solution, list(problem.test_cases)
            )
            if not result.passed:
                reason = {"stage": "execution", "execution": result.to_dict()}
        if reason is None:
            valid.append(problem)
        else:
            quarantined.append(problem)
            record = {"problem": problem.to_dict(), "failure": reason}
            records.append(record)
            LOGGER.warning("Quarantined %s: %s", problem.task_id, reason["stage"])

    destination = Path(quarantine_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return ValidationSummary(tuple(valid), tuple(quarantined))
