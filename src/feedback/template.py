"""Category-specific deterministic templates for execution feedback."""

from __future__ import annotations

from execution.base import ExecutionResult, TestResult
from feedback.classifier import Classification, ErrorCategory


class TemplateFeedbackGenerator:
    """Render concise feedback without model-based judgment."""

    def generate(
        self, classification: Classification, execution: ExecutionResult
    ) -> str:
        """Return feedback appropriate to the deterministic error category."""

        category = classification.category
        if category is ErrorCategory.SUCCESS:
            return "All assertions passed."
        if category is ErrorCategory.SYNTAX:
            return self._exception_feedback("syntax error", execution)
        if category is ErrorCategory.TIMEOUT:
            return self._exception_feedback(
                "timeout; make the implementation terminate within the limit",
                execution,
            )
        if category is ErrorCategory.RUNTIME:
            return self._exception_feedback("runtime exception", execution)

        heading = (
            "The solution failed every assertion. Reconsider the core algorithm."
            if category is ErrorCategory.LOGIC
            else "The core approach is partly correct, but it fails specific cases."
        )
        failed = [test for test in execution.tests if not test.passed]
        details = "\n".join(
            self._assertion_detail(index, test)
            for index, test in enumerate(failed, start=1)
        )
        return (
            f"{heading}\n"
            f"Passed {classification.passed_assertions}/"
            f"{classification.total_assertions} assertions.\n"
            f"Failed assertions:\n{details}"
        )

    @staticmethod
    def strategy_for(
        classification: Classification, execution: ExecutionResult | None = None
    ) -> str:
        """Return the effective strategy label persisted with an iteration."""

        del classification, execution
        return "template"

    @staticmethod
    def _assertion_detail(index: int, test: TestResult) -> str:
        expression = test.assertion_expression or _assertion_line(test.test_case)
        detail = f"{index}. {expression}"
        if test.actual_value is not None and test.expected_value is not None:
            detail += (
                f"\n   actual: {test.actual_value}"
                f"\n   expected: {test.expected_value}"
            )
        elif test.exception_message:
            detail += f"\n   error: {test.exception_message}"
        return detail

    @staticmethod
    def _exception_feedback(label: str, execution: ExecutionResult) -> str:
        failed = next((test for test in execution.tests if not test.passed), None)
        if failed is None:
            return f"Execution reported a {label}."
        exception = failed.exception_type or "unknown exception"
        message = f": {failed.exception_message}" if failed.exception_message else ""
        return f"Execution reported a {label}. {exception}{message}"


def _assertion_line(test_case: str) -> str:
    return next(
        (
            line.strip()
            for line in test_case.splitlines()
            if line.strip().startswith("assert ")
        ),
        test_case.strip(),
    )
