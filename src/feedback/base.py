"""Shared interface for deterministic execution-feedback strategies."""

from __future__ import annotations

from typing import Protocol

from execution.base import ExecutionResult
from feedback.classifier import Classification


class FeedbackGenerator(Protocol):
    """Structural interface implemented by every feedback strategy."""

    def generate(
        self, classification: Classification, execution: ExecutionResult
    ) -> str:
        """Render feedback from deterministic execution evidence."""

    def strategy_for(
        self,
        classification: Classification,
        execution: ExecutionResult | None = None,
    ) -> str:
        """Return the effective strategy used for this execution outcome."""
