"""Unified benchmark problem schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Problem:
    """Normalized HumanEval or sanitized MBPP programming task."""

    task_id: str
    prompt: str
    canonical_solution: str
    test_cases: tuple[str, ...]
    difficulty: str
    tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the exact unified JSON representation."""

        data = asdict(self)
        data["test_cases"] = list(self.test_cases)
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Problem:
        """Construct a problem from its unified JSON representation."""

        expected = {
            "task_id",
            "prompt",
            "canonical_solution",
            "test_cases",
            "difficulty",
            "tags",
        }
        if set(data) != expected:
            raise ValueError(f"Problem fields must be exactly {sorted(expected)}")
        return cls(
            task_id=str(data["task_id"]),
            prompt=str(data["prompt"]),
            canonical_solution=str(data["canonical_solution"]),
            test_cases=tuple(str(case) for case in data["test_cases"]),
            difficulty=str(data["difficulty"]),
            tags=tuple(str(tag) for tag in data["tags"]),
        )
