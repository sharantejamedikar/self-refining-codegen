"""Config-driven construction of deterministic feedback strategies."""

from __future__ import annotations

from feedback.base import FeedbackGenerator
from feedback.hybrid import HybridFeedbackGenerator
from feedback.template import TemplateFeedbackGenerator
from feedback.trace import TraceFeedbackGenerator


def create_feedback_generator(strategy: str) -> FeedbackGenerator:
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
    return generator()
