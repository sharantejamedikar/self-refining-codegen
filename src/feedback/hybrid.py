"""Rule-based hybrid selection between template and trace feedback."""

from __future__ import annotations

from execution.base import ExecutionResult
from feedback.classifier import Classification, ErrorCategory
from feedback.template import TemplateFeedbackGenerator
from feedback.trace import TraceFeedbackGenerator


class HybridFeedbackGenerator:
    """Select trace feedback only for complex, evidence-rich failures."""

    def __init__(self) -> None:
        self._template = TemplateFeedbackGenerator()
        self._trace = TraceFeedbackGenerator()

    def generate(
        self, classification: Classification, execution: ExecutionResult
    ) -> str:
        """Render feedback using the fixed deterministic category rule."""

        generator = (
            self._trace
            if self.strategy_for(classification, execution) == "trace"
            else self._template
        )
        return generator.generate(classification, execution)

    @staticmethod
    def strategy_for(
        classification: Classification, execution: ExecutionResult | None = None
    ) -> str:
        """Use traces for logic, edge cases, and recursion-style runtime errors."""

        if classification.category in {ErrorCategory.LOGIC, ErrorCategory.EDGE_CASE}:
            return "trace"
        if classification.category is ErrorCategory.RUNTIME and execution is not None:
            complex_runtime_types = {"RecursionError"}
            if any(
                not test.passed and test.exception_type in complex_runtime_types
                for test in execution.tests
            ):
                return "trace"
        return "template"
