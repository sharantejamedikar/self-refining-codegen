"""Backend-neutral code generation interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GenerationRequest:
    """Model-neutral input for one candidate generation."""

    problem_prompt: str
    seed: int


@dataclass(frozen=True)
class GenerationOutput:
    """Extracted candidate, raw response, and backend-neutral accounting."""

    code: str
    raw_text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    extraction_method: str = "unchanged"
    syntax_valid: bool = True
    backend_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


class Generator(ABC):
    """Abstract code-generation backend."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationOutput:
        """Generate one candidate without exposing backend details to callers."""
