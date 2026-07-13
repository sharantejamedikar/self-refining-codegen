"""Execution-feedback classification and generation."""

from feedback.base import FeedbackGenerator
from feedback.classifier import Classification, ErrorCategory, classify_execution
from feedback.factory import create_feedback_generator
from feedback.hybrid import HybridFeedbackGenerator
from feedback.template import TemplateFeedbackGenerator
from feedback.trace import TraceFeedbackGenerator

__all__ = [
    "Classification",
    "ErrorCategory",
    "FeedbackGenerator",
    "HybridFeedbackGenerator",
    "TemplateFeedbackGenerator",
    "TraceFeedbackGenerator",
    "classify_execution",
    "create_feedback_generator",
]
