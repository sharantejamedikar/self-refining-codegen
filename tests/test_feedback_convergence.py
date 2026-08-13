"""Tests for deterministic classification, feedback, and convergence."""

from __future__ import annotations

import pytest

from convergence import (
    ConvergenceDetector,
    ConvergenceReason,
    IterationRecord,
    stable_hash,
)
from execution import ExecutionResult, SubprocessExecutor
from execution import TestResult as ExecutionTestResult
from feedback import (
    Classification,
    ErrorCategory,
    HybridFeedbackGenerator,
    TemplateFeedbackGenerator,
    TraceFeedbackGenerator,
    classify_execution,
    create_feedback_generator,
)


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


def test_feedback_factory_applies_configured_word_ceiling() -> None:
    execution = _execution(_test_result(), _test_result())
    classification = classify_execution(execution)
    generator = create_feedback_generator("hybrid", max_words=7)

    feedback = generator.generate(classification, execution)

    assert len(feedback.split()) == 7
    assert generator.strategy_for(classification, execution) == "trace"


def test_feedback_uses_traceback_matched_assertion_for_compound_harness() -> None:
    """Report the later assertion that failed, not the harness's first assertion."""

    compound_harness = """\
def check(candidate):
    assert candidate(1) == 1
    assert candidate(2) == 99

check(candidate)
"""
    execution = SubprocessExecutor(
        timeout_seconds=1, memory_limit_mb=None, collect_trace=True
    ).execute(
        "def candidate(value):\n    return value",
        [compound_harness],
    )
    failed = execution.tests[0]
    feedback = TraceFeedbackGenerator().generate(
        classify_execution(execution), execution
    )

    assert failed.assertion_expression == "candidate(2) == 99"
    assert "1. candidate(2) == 99" in feedback
    assert "candidate(1) == 1" not in feedback


@pytest.mark.parametrize(
    ("result", "category", "expected"),
    [
        (
            _test_result(exception_type="SyntaxError"),
            ErrorCategory.SYNTAX,
            "Execution reported a syntax error. SyntaxError: failure",
        ),
        (
            _test_result(exception_type="TimeoutError", timed_out=True),
            ErrorCategory.TIMEOUT,
            "Execution reported a timeout; make the implementation terminate "
            "within the limit. TimeoutError: failure",
        ),
        (
            _test_result(exception_type="ValueError"),
            ErrorCategory.RUNTIME,
            "Execution reported a runtime exception. ValueError: failure",
        ),
    ],
)
def test_template_feedback_for_exception_categories(
    result: ExecutionTestResult, category: ErrorCategory, expected: str
) -> None:
    """Render actionable text for every non-assertion failure category."""

    execution = _execution(result)
    classification = classify_execution(execution)
    assert classification.category is category
    assert TemplateFeedbackGenerator().generate(classification, execution) == expected


def test_template_feedback_assertion_fallbacks() -> None:
    """Retain useful assertion context when structured values are unavailable."""

    with_assertion = ExecutionTestResult(
        test_case="setup()\nassert candidate(2) == 5",
        passed=False,
        exception_type="AssertionError",
        exception_message="unexpected value",
        traceback=None,
        stdout="",
        stderr="",
        duration_seconds=0.01,
    )
    without_assertion = ExecutionTestResult(
        test_case="check_candidate()",
        passed=False,
        exception_type="AssertionError",
        exception_message=None,
        traceback=None,
        stdout="",
        stderr="",
        duration_seconds=0.01,
    )
    execution = _execution(with_assertion, without_assertion)
    feedback = TemplateFeedbackGenerator().generate(
        classify_execution(execution), execution
    )
    assert "1. assert candidate(2) == 5\n   error: unexpected value" in feedback
    assert "2. check_candidate()" in feedback


def test_exception_feedback_defensive_fallbacks() -> None:
    """Remain deterministic for incomplete or internally inconsistent results."""

    generator = TemplateFeedbackGenerator()
    runtime = Classification(ErrorCategory.RUNTIME, 0, 0)
    assert generator.generate(runtime, _execution()) == (
        "Execution reported a runtime exception."
    )

    unknown = ExecutionTestResult(
        test_case="candidate()",
        passed=False,
        exception_type=None,
        exception_message=None,
        traceback=None,
        stdout="",
        stderr="",
        duration_seconds=0.01,
    )
    assert generator.generate(runtime, _execution(unknown)) == (
        "Execution reported a runtime exception. unknown exception"
    )


def test_trace_feedback_identifies_candidate_operation() -> None:
    execution = SubprocessExecutor(
        timeout_seconds=1, memory_limit_mb=None, collect_trace=True
    ).execute(
        "def candidate(value):\n    doubled = value * 2\n    return doubled + 1",
        ["assert candidate(3) == 6"],
    )
    feedback = TraceFeedbackGenerator().generate(
        classify_execution(execution), execution
    )
    assert "Observed divergence" in feedback
    assert "actual: 7" in feedback and "expected: 6" in feedback
    assert "return doubled + 1" in feedback
    assert "candidate" in feedback


def test_trace_feedback_reports_recursion_depth_and_restructuring_hint() -> None:
    execution = SubprocessExecutor(
        timeout_seconds=1, memory_limit_mb=None, collect_trace=True
    ).execute(
        "def candidate(value):\n    return candidate(value + 1)",
        ["candidate(0)"],
    )
    feedback = TraceFeedbackGenerator().generate(
        classify_execution(execution), execution
    )
    assert "RecursionError" in feedback
    assert "candidate call depth" in feedback
    assert "restructuring" in feedback


@pytest.mark.parametrize(
    ("category", "expected_strategy"),
    [
        (ErrorCategory.SYNTAX, "template"),
        (ErrorCategory.RUNTIME, "template"),
        (ErrorCategory.LOGIC, "trace"),
        (ErrorCategory.EDGE_CASE, "trace"),
        (ErrorCategory.TIMEOUT, "template"),
        (ErrorCategory.SUCCESS, "template"),
    ],
)
def test_hybrid_feedback_selector(
    category: ErrorCategory, expected_strategy: str
) -> None:
    generator = HybridFeedbackGenerator()
    classification = Classification(category, 0, 1)
    assert generator.strategy_for(classification) == expected_strategy


def test_hybrid_routes_recursion_as_complex_runtime() -> None:
    execution = _execution(_test_result(exception_type="RecursionError"))
    classification = classify_execution(execution)
    assert HybridFeedbackGenerator().strategy_for(classification, execution) == "trace"


def test_feedback_factory() -> None:
    assert isinstance(create_feedback_generator("template"), TemplateFeedbackGenerator)
    assert isinstance(create_feedback_generator("trace"), TraceFeedbackGenerator)
    assert isinstance(create_feedback_generator("hybrid"), HybridFeedbackGenerator)
    with pytest.raises(ValueError, match="Unsupported feedback strategy"):
        create_feedback_generator("unknown")


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
