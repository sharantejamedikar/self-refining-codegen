"""Model-neutral prompt strategies for code generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RenderedPrompt:
    """System and user text ready for a chat-aware backend."""

    system: str
    user: str


_SYSTEM_PROMPT = (
    "You are a Python code generation system. Return only the complete Python "
    "solution, without Markdown fences or explanatory prose. Preserve the requested "
    "function name and signature."
)

# Synthetic teaching examples written for this project. They are not benchmark items.
_FEW_SHOT_EXAMPLES: tuple[tuple[str, str], ...] = (
    (
        "def clamp_integer(value: int, lower: int, upper: int) -> int:\n"
        '    """Clamp value to the inclusive interval [lower, upper]."""',
        "def clamp_integer(value: int, lower: int, upper: int) -> int:\n"
        "    return max(lower, min(value, upper))",
    ),
    (
        "def alternating_case(text: str) -> str:\n"
        '    """Uppercase even-indexed characters and lowercase odd ones."""',
        "def alternating_case(text: str) -> str:\n"
        "    return ''.join(\n"
        "        char.upper() if index % 2 == 0 else char.lower()\n"
        "        for index, char in enumerate(text)\n"
        "    )",
    ),
    (
        "def unique_in_order(values: list[int]) -> list[int]:\n"
        '    """Remove adjacent duplicates while preserving order."""',
        "def unique_in_order(values: list[int]) -> list[int]:\n"
        "    result = []\n"
        "    for value in values:\n"
        "        if not result or result[-1] != value:\n"
        "            result.append(value)\n"
        "    return result",
    ),
)


def build_prompt(
    problem_prompt: str,
    strategy: Literal["zero_shot", "few_shot"] = "zero_shot",
    few_shot_examples: int = 2,
    previous_code: str | None = None,
    feedback: str | None = None,
) -> RenderedPrompt:
    """Render a zero-shot or synthetic few-shot prompt without model-specific text."""

    if strategy not in {"zero_shot", "few_shot"}:
        raise ValueError(f"Unsupported prompt strategy: {strategy}")
    if not 0 <= few_shot_examples <= len(_FEW_SHOT_EXAMPLES):
        raise ValueError(
            f"few_shot_examples must be between 0 and {len(_FEW_SHOT_EXAMPLES)}"
        )

    sections: list[str] = []
    if strategy == "few_shot":
        for example_prompt, example_solution in _FEW_SHOT_EXAMPLES[:few_shot_examples]:
            sections.append(
                f"Example problem:\n{example_prompt}\n\n"
                f"Example solution:\n{example_solution}"
            )
    problem_section = f"Problem:\n{problem_prompt.rstrip()}"
    if feedback is not None:
        if previous_code is None:
            raise ValueError("previous_code is required when feedback is provided")
        problem_section += (
            f"\n\nPrevious solution:\n{previous_code.rstrip()}"
            f"\n\nExecution feedback:\n{feedback.rstrip()}"
            "\n\nReturn a corrected complete solution."
        )
    sections.append(f"{problem_section}\n\nSolution:")
    return RenderedPrompt(system=_SYSTEM_PROMPT, user="\n\n".join(sections))
