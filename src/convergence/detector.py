"""Deterministic stopping rules for iterative code refinement."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


class ConvergenceReason(str, Enum):
    """Terminal and non-terminal convergence decisions."""

    CONTINUE = "continue"
    SUCCESS = "success"
    MAX_ITERATIONS = "max_iterations"
    STAGNATION = "stagnation"
    OSCILLATION = "oscillation"
    FIXED_ITERATIONS_COMPLETE = "fixed_iterations_complete"


@dataclass(frozen=True)
class IterationRecord:
    """Minimal deterministic state needed for convergence checks."""

    iteration: int
    code_hash: str
    passed_assertions: int
    total_assertions: int
    error_hash: str
    success: bool


class ConvergenceDetector:
    """Apply stopping conditions in the project-mandated priority order."""

    def __init__(
        self, max_iterations: int, stagnation_patience: int, oscillation_window: int
    ) -> None:
        if min(max_iterations, stagnation_patience, oscillation_window) <= 0:
            raise ValueError("convergence settings must be positive")
        self.max_iterations = max_iterations
        self.stagnation_patience = stagnation_patience
        self.oscillation_window = oscillation_window

    def decide(self, records: list[IterationRecord]) -> ConvergenceReason:
        """Return the decision for the latest record."""

        if not records:
            raise ValueError("At least one iteration record is required")
        latest = records[-1]
        if latest.success:
            return ConvergenceReason.SUCCESS
        if latest.iteration >= self.max_iterations:
            return ConvergenceReason.MAX_ITERATIONS
        if self._stagnant(records):
            return ConvergenceReason.STAGNATION
        recent = records[max(0, len(records) - 1 - self.oscillation_window) : -1]
        if any(record.code_hash == latest.code_hash for record in recent):
            return ConvergenceReason.OSCILLATION
        return ConvergenceReason.CONTINUE

    def _stagnant(self, records: list[IterationRecord]) -> bool:
        required = self.stagnation_patience + 1
        if len(records) < required:
            return False
        recent = records[-required:]
        latest = recent[-1]
        return all(
            (record.passed_assertions, record.total_assertions, record.error_hash)
            == (latest.passed_assertions, latest.total_assertions, latest.error_hash)
            for record in recent
        )


def stable_hash(value: str) -> str:
    """Return a stable SHA-256 hex digest."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
