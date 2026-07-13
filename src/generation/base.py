"""Backend-neutral code generation interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GenerationOutput:
    """Text and accounting returned by a generation backend."""

    code: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


class Generator(ABC):
    """Abstract code-generation backend."""

    @abstractmethod
    def generate(self, prompt: str, seed: int) -> GenerationOutput:
        """Generate one candidate for a prompt and deterministic seed."""
