"""Tests for contamination-safe prompts and conservative code extraction."""

from __future__ import annotations

import ast

import pytest

from generation.extraction import extract_python
from generation.prompts import build_prompt

PROBLEM = 'def increment(value: int) -> int:\n    """Return value plus one."""'


def test_zero_shot_contains_only_target_problem() -> None:
    prompt = build_prompt(PROBLEM)
    assert PROBLEM in prompt.user
    assert "Example problem" not in prompt.user
    assert "Return only" in prompt.system


def test_few_shot_uses_requested_synthetic_examples() -> None:
    prompt = build_prompt(PROBLEM, "few_shot", 3)
    assert prompt.user.count("Example problem:") == 3
    assert "clamp_integer" in prompt.user
    assert "HumanEval" not in prompt.user and "MBPP" not in prompt.user


def test_prompt_builder_rejects_invalid_options() -> None:
    with pytest.raises(ValueError, match="strategy"):
        build_prompt(PROBLEM, "invalid")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="between"):
        build_prompt(PROBLEM, "few_shot", 4)


def test_refinement_prompt_includes_previous_code_and_feedback() -> None:
    rendered = build_prompt(
        "def answer(): pass",
        previous_code="def answer(): return 0",
        feedback="Expected 1, got 0.",
    )
    assert "Previous solution:\ndef answer(): return 0" in rendered.user
    assert "Execution feedback:\nExpected 1, got 0." in rendered.user
    with pytest.raises(ValueError, match="previous_code"):
        build_prompt("def answer(): pass", feedback="broken")


def test_extracts_markdown_and_unclosed_fences() -> None:
    fenced = extract_python(
        "Here is the answer:\n```python\n"
        "def increment(value):\n    return value + 1\n```\nDone.",
        PROBLEM,
    )
    unclosed = extract_python(
        "```py\ndef increment(value):\n    return value + 1", PROBLEM
    )
    assert fenced.method == "markdown_fence" and fenced.syntax_valid
    assert unclosed.method == "unclosed_markdown_fence" and unclosed.syntax_valid


def test_extracts_unfenced_prose_wrapped_code() -> None:
    result = extract_python(
        "A concise implementation follows.\n\ndef increment(value):\n"
        "    return value + 1\n\nThis handles integers.",
        PROBLEM,
    )
    assert result.method == "prose_wrapped"
    assert result.code.endswith("return value + 1")
    ast.parse(result.code)


def test_restores_prompt_grounded_signature_and_completion_body() -> None:
    restored = extract_python("def increment(value\n    return value + 1", PROBLEM)
    completion = extract_python("return value + 1", PROBLEM)
    assert restored.method == "prompt_signature_restored"
    assert restored.code.startswith("def increment(value: int) -> int:")
    assert completion.method == "prompt_body_completion"
    assert completion.code.startswith("def increment(value: int) -> int:")
    ast.parse(restored.code)
    ast.parse(completion.code)


def test_invalid_response_remains_auditable_failure() -> None:
    result = extract_python("This is not Python and has no solution.", PROBLEM)
    assert result.method == "unparsed_fallback"
    assert not result.syntax_valid
    assert result.code == "This is not Python and has no solution."
