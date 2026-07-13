"""Backend-neutral types for executing untrusted generated programs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    """One recently executed candidate-code line captured in the sandbox."""

    line_number: int
    function: str
    source: str


@dataclass(frozen=True)
class ExecutionTrace:
    """Bounded candidate execution evidence collected by a sandbox tracer."""

    recent_events: tuple[TraceEvent, ...]
    max_call_depth: int
    deepest_function: str | None


@dataclass(frozen=True)
class TestResult:
    """Outcome of one isolated test case."""

    test_case: str
    passed: bool
    exception_type: str | None
    exception_message: str | None
    traceback: str | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    assertion_expression: str | None = None
    actual_value: str | None = None
    expected_value: str | None = None
    trace: ExecutionTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


@dataclass(frozen=True)
class ExecutionResult:
    """Structured aggregate from executing all tests for one candidate."""

    passed: bool
    tests: tuple[TestResult, ...]
    duration_seconds: float

    @property
    def passed_tests(self) -> int:
        """Return the number of passing tests."""

        return sum(test.passed for test in self.tests)

    @property
    def total_tests(self) -> int:
        """Return the number of executed tests."""

        return len(self.tests)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "passed": self.passed,
            "passed_tests": self.passed_tests,
            "total_tests": self.total_tests,
            "duration_seconds": self.duration_seconds,
            "tests": [test.to_dict() for test in self.tests],
        }


class Executor(ABC):
    """Abstract execution boundary for untrusted candidate code."""

    @abstractmethod
    def execute(self, code: str, test_cases: list[str]) -> ExecutionResult:
        """Execute each test in isolation and return structured outcomes."""
