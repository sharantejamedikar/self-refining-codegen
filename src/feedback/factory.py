"""Config-driven construction of deterministic feedback strategies."""

from __future__ import annotations

from execution.base import ExecutionResult
from feedback.base import FeedbackGenerator
from feedback.classifier import Classification
from feedback.hybrid import HybridFeedbackGenerator
from feedback.template import TemplateFeedbackGenerator
from feedback.trace import TraceFeedbackGenerator


class BoundedFeedbackGenerator:
    """Apply a deterministic word ceiling to another feedback strategy."""

    def __init__(self, delegate: FeedbackGenerator, max_words: int) -> None:
        self._delegate = delegate
        self._max_words = max_words

    def generate(
        self, classification: Classification, execution: ExecutionResult
    ) -> str:
        """Return complete feedback up to the configured word ceiling."""

        words = self._delegate.generate(classification, execution).split()
        return " ".join(words[: self._max_words])

    def strategy_for(
        self,
        classification: Classification,
        execution: ExecutionResult | None = None,
    ) -> str:
        """Preserve the effective strategy label of the wrapped generator."""

        return self._delegate.strategy_for(classification, execution)


def create_feedback_generator(
    strategy: str, max_words: int | None = None
) -> FeedbackGenerator:
    """Create the named feedback strategy or reject unsupported names."""

    generators: dict[str, type[FeedbackGenerator]] = {
        "template": TemplateFeedbackGenerator,
        "trace": TraceFeedbackGenerator,
        "hybrid": HybridFeedbackGenerator,
    }
    try:
        generator = generators[strategy]
    except KeyError as error:
        raise ValueError(f"Unsupported feedback strategy: {strategy!r}") from error
    instance = generator()
    return BoundedFeedbackGenerator(instance, max_words) if max_words else instance
