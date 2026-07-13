"""Execution-feedback classification and generation."""

from feedback.classifier import Classification, ErrorCategory, classify_execution
from feedback.template import TemplateFeedbackGenerator

__all__ = [
    "Classification",
    "ErrorCategory",
    "TemplateFeedbackGenerator",
    "classify_execution",
]
