"""Deterministic execution-result error classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from execution.base import ExecutionResult


class ErrorCategory(str, Enum):
    """Mutually exclusive outcome categories used by refinement."""

    SYNTAX = "syntax"
    TIMEOUT = "timeout"
    RUNTIME = "runtime"
    LOGIC = "logic"
    EDGE_CASE = "edge_case"
    SUCCESS = "success"


@dataclass(frozen=True)
class Classification:
    """A category plus assertion-level diagnostic counts."""

    category: ErrorCategory
    passed_assertions: int
    total_assertions: int

    @property
    def pass_rate(self) -> float:
        """Return diagnostic assertion pass rate, never the headline metric."""

        if self.total_assertions == 0:
            return 0.0
        return self.passed_assertions / self.total_assertions


def classify_execution(result: ExecutionResult) -> Classification:
    """Classify an execution result using the fixed deterministic priority."""

    tests = result.tests
    passed = result.passed_tests
    total = result.total_tests
    exception_types = {test.exception_type for test in tests if not test.passed}
    if "SyntaxError" in exception_types:
        category = ErrorCategory.SYNTAX
    elif any(test.timed_out for test in tests):
        category = ErrorCategory.TIMEOUT
    elif any(
        not test.passed and test.exception_type != "AssertionError" for test in tests
    ):
        category = ErrorCategory.RUNTIME
    elif result.passed and total > 0:
        category = ErrorCategory.SUCCESS
    elif passed == 0:
        category = ErrorCategory.LOGIC
    else:
        category = ErrorCategory.EDGE_CASE
    return Classification(category, passed, total)
