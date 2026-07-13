"""Explicit canned generator used by tests and GPU-free M1 runs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from data.schema import Problem
from generation.base import GenerationOutput, GenerationRequest, Generator
from generation.prompts import build_prompt


class MockGenerator(Generator):
    """Return prompt-indexed canned code without loading any model."""

    def __init__(
        self, outputs: Mapping[str, str], default_output: str | None = None
    ) -> None:
        self._outputs = dict(outputs)
        self._default_output = default_output

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        """Return the configured output for a model-neutral request."""

        if request.problem_prompt in self._outputs:
            code = self._outputs[request.problem_prompt]
        elif self._default_output is not None:
            code = self._default_output
        else:
            raise KeyError("No canned MockGenerator output for this prompt")
        rendered = build_prompt(
            request.problem_prompt,
            previous_code=request.previous_code,
            feedback=request.feedback,
        )
        return GenerationOutput(
            code=code,
            raw_text=code,
            rendered_system_prompt=rendered.system,
            rendered_user_prompt=rendered.user,
        )

    @classmethod
    def canned_correct(cls, problems: Iterable[Problem]) -> MockGenerator:
        """Build an explicit oracle-like mock from canonical fixture outputs."""

        return cls({problem.prompt: problem.canonical_solution for problem in problems})

    @classmethod
    def canned_buggy(cls, problems: Iterable[Problem]) -> MockGenerator:
        """Build a mock returning a deterministic assertion-triggering program."""

        return cls(
            {
                problem.prompt: "raise AssertionError('canned buggy output')"
                for problem in problems
            }
        )
