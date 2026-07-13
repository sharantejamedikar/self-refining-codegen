"""Tests for deterministic classification, feedback, and convergence."""

from __future__ import annotations

from convergence import (
    ConvergenceDetector,
    ConvergenceReason,
    IterationRecord,
    stable_hash,
)
from execution import ExecutionResult, SubprocessExecutor
from execution import TestResult as ExecutionTestResult
from feedback import ErrorCategory, TemplateFeedbackGenerator, classify_execution


def _test_result(
    *,
    passed: bool = False,
    exception_type: str | None = "AssertionError",
    timed_out: bool = False,
) -> ExecutionTestResult:
    return ExecutionTestResult(
        test_case="assert candidate(2) == 5",
        passed=passed,
        exception_type=None if passed else exception_type,
        exception_message=None if passed else "failure",
        traceback=None,
        stdout="",
        stderr="",
        duration_seconds=0.01,
        timed_out=timed_out,
    )


def _execution(*tests: ExecutionTestResult) -> ExecutionResult:
    return ExecutionResult(
        passed=bool(tests) and all(test.passed for test in tests),
        tests=tests,
        duration_seconds=0.01,
    )


def test_classifier_categories_and_priority() -> None:
    syntax = _test_result(exception_type="SyntaxError")
    timeout = _test_result(exception_type="TimeoutError", timed_out=True)
    runtime = _test_result(exception_type="ValueError")
    failed = _test_result()
    passed = _test_result(passed=True)

    assert (
        classify_execution(_execution(syntax, timeout)).category is ErrorCategory.SYNTAX
    )
    assert (
        classify_execution(_execution(timeout, runtime)).category
        is ErrorCategory.TIMEOUT
    )
    assert (
        classify_execution(_execution(runtime, failed)).category
        is ErrorCategory.RUNTIME
    )
    logic = classify_execution(_execution(failed, failed))
    assert logic.category is ErrorCategory.LOGIC and logic.pass_rate == 0.0
    edge = classify_execution(_execution(passed, failed))
    assert edge.category is ErrorCategory.EDGE_CASE and edge.pass_rate == 0.5
    assert classify_execution(_execution(passed)).category is ErrorCategory.SUCCESS


def test_template_feedback_includes_assertion_actual_and_expected() -> None:
    execution = SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None).execute(
        "def candidate(value):\n    return value + 1",
        ["assert candidate(2) == 5", "assert candidate(1) == 2"],
    )
    classification = classify_execution(execution)
    feedback = TemplateFeedbackGenerator().generate(classification, execution)
    assert classification.category is ErrorCategory.EDGE_CASE
    assert "candidate(2) == 5" in feedback
    assert "actual: 3" in feedback
    assert "expected: 5" in feedback
    assert "Passed 1/2" in feedback


def _record(
    iteration: int,
    code: str,
    passed: int = 0,
    error: str = "same",
    success: bool = False,
) -> IterationRecord:
    return IterationRecord(
        iteration=iteration,
        code_hash=stable_hash(code),
        passed_assertions=passed,
        total_assertions=2,
        error_hash=stable_hash(error),
        success=success,
    )


def test_convergence_priority_and_conditions() -> None:
    detector = ConvergenceDetector(5, 2, 3)
    assert detector.decide([_record(1, "a")]) is ConvergenceReason.CONTINUE
    assert detector.decide([_record(1, "a"), _record(2, "a")]) is (
        ConvergenceReason.OSCILLATION
    )
    stagnant = [_record(1, "a"), _record(2, "b"), _record(3, "c")]
    assert detector.decide(stagnant) is ConvergenceReason.STAGNATION
    maxed = [*stagnant, _record(4, "d"), _record(5, "e")]
    assert detector.decide(maxed) is ConvergenceReason.MAX_ITERATIONS
    successful = [*stagnant, _record(4, "d"), _record(5, "e", success=True)]
    assert detector.decide(successful) is ConvergenceReason.SUCCESS
