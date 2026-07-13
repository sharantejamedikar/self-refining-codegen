"""Trace-enriched deterministic feedback for complex execution failures."""

from __future__ import annotations

from execution.base import ExecutionResult, TestResult, TraceEvent
from feedback.classifier import Classification, ErrorCategory
from feedback.template import TemplateFeedbackGenerator


class TraceFeedbackGenerator:
    """Combine assertion/exception evidence with sandboxed candidate traces."""

    def __init__(self) -> None:
        self._template = TemplateFeedbackGenerator()

    def generate(
        self, classification: Classification, execution: ExecutionResult
    ) -> str:
        """Render bounded trace evidence without inferring unobserved state."""

        baseline = self._template.generate(classification, execution)
        if classification.category is ErrorCategory.SUCCESS:
            return baseline

        failed = [test for test in execution.tests if not test.passed]
        if not failed:
            return baseline + "\nNo failed-test trace was available."
        details = [
            self._trace_detail(index, test) for index, test in enumerate(failed, 1)
        ]
        return f"{baseline}\nTrace analysis:\n" + "\n".join(details)

    @staticmethod
    def strategy_for(
        classification: Classification, execution: ExecutionResult | None = None
    ) -> str:
        """Return the effective strategy label persisted with an iteration."""

        del classification, execution
        return "trace"

    @staticmethod
    def _trace_detail(index: int, test: TestResult) -> str:
        lines = [f"{index}. {_failure_label(test)}"]
        if test.actual_value is not None and test.expected_value is not None:
            lines.append(
                "   Observed divergence: "
                f"actual: {test.actual_value}; expected: {test.expected_value}."
            )

        trace = test.trace
        if trace is None:
            traceback_line = _candidate_traceback_line(test.traceback)
            if traceback_line:
                lines.append(f"   Candidate traceback location: {traceback_line}")
            else:
                lines.append("   No candidate line trace was captured.")
            return "\n".join(lines)

        operation = _last_meaningful_event(trace.recent_events)
        if operation is not None:
            lines.append(
                f"   Last candidate operation: line {operation.line_number} "
                f"in {operation.function}: {operation.source}"
            )
        if test.exception_type == "RecursionError":
            function = trace.deepest_function or "candidate function"
            lines.append(
                f"   Recursion reached candidate call depth {trace.max_call_depth} "
                f"in {function}. Repeated recursion at this depth indicates the "
                "approach may need restructuring (for example, an iterative or "
                "partition-based algorithm), not merely retrying the same recursion."
            )
        return "\n".join(lines)


def _failure_label(test: TestResult) -> str:
    expression = test.assertion_expression
    if expression:
        return f"Failed assertion: {expression}"
    exception = test.exception_type or "execution failure"
    message = f": {test.exception_message}" if test.exception_message else ""
    return f"{exception}{message}"


def _last_meaningful_event(events: tuple[TraceEvent, ...]) -> TraceEvent | None:
    return next((event for event in reversed(events) if event.source), None)


def _candidate_traceback_line(traceback: str | None) -> str | None:
    if not traceback:
        return None
    locations = [
        line.strip()
        for line in traceback.splitlines()
        if line.lstrip().startswith('File "') and "program.py" in line
    ]
    return locations[-1] if locations else None
