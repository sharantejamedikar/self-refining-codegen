"""Conservative extraction of executable Python from model responses."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionResult:
    """Extracted candidate plus an auditable extraction decision."""

    code: str
    method: str
    syntax_valid: bool


_FENCE_PATTERN = re.compile(
    r"```(?P<label>[^\n`]*)\n(?P<code>.*?)(?:```|\Z)", re.DOTALL
)
_CODE_START = re.compile(
    r"^\s*(?:from\s+\S+\s+import\s+|import\s+|async\s+def\s+|def\s+|" r"class\s+|@\w+)",
)
_BODY_START = re.compile(r"^\s*(?:return\b|raise\b|if\b|for\b|while\b|try:|with\b)")
_FUNCTION_NAME = re.compile(r"(?m)^\s*(?:async\s+)?def\s+(?P<name>[A-Za-z_]\w*)")


def extract_python(raw_text: str, problem_prompt: str) -> ExtractionResult:
    """Extract Python while avoiding speculative repairs of model logic."""

    raw = raw_text.strip()
    fenced = list(_FENCE_PATTERN.finditer(raw))
    expected_signature = _signature_line(problem_prompt)
    expected_name = (
        _function_name(expected_signature) if expected_signature is not None else None
    )
    fenced.sort(
        key=lambda match: (
            match.group("label").strip().lower() not in {"python", "py"},
            expected_name is not None
            and f"def {expected_name}" not in match.group("code"),
            -len(match.group("code")),
        )
    )
    for match in fenced:
        code = match.group("code").strip()
        if _is_parseable(code):
            method = (
                "markdown_fence"
                if match.group(0).rstrip().endswith("```")
                else "unclosed_markdown_fence"
            )
            return ExtractionResult(code, method, True)

    if _is_parseable(raw):
        return ExtractionResult(raw, "raw", True)

    candidates = [match.group("code").strip() for match in fenced]
    candidates.append(raw)
    for candidate in candidates:
        prose_code = _extract_parseable_code_region(candidate)
        if prose_code is not None:
            return ExtractionResult(prose_code, "prose_wrapped", True)

        signature_repair = _restore_prompt_signature(candidate, problem_prompt)
        if signature_repair is not None and _is_parseable(signature_repair):
            return ExtractionResult(signature_repair, "prompt_signature_restored", True)

        completion = _combine_prompt_and_body(candidate, problem_prompt)
        if completion is not None and _is_parseable(completion):
            return ExtractionResult(completion, "prompt_body_completion", True)

    fallback = candidates[0] if candidates and candidates[0] else raw
    return ExtractionResult(fallback, "unparsed_fallback", False)


def _extract_parseable_code_region(text: str) -> str | None:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if _CODE_START.match(line)]
    for start in starts:
        for end in range(len(lines), start, -1):
            candidate = "\n".join(lines[start:end]).strip()
            if _is_parseable(candidate):
                return candidate
    return None


def _restore_prompt_signature(text: str, problem_prompt: str) -> str | None:
    expected = _signature_line(problem_prompt)
    if expected is None:
        return None
    expected_name = _function_name(expected)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = _FUNCTION_NAME.match(line)
        if match and match.group("name") == expected_name:
            lines[index] = expected
            return "\n".join(lines).strip()
    return None


def _combine_prompt_and_body(text: str, problem_prompt: str) -> str | None:
    stripped = text.strip()
    if not stripped or _FUNCTION_NAME.search(stripped):
        return None
    first_line = stripped.splitlines()[0]
    if not (_BODY_START.match(first_line) or text[:1].isspace()):
        return None
    body = textwrap.indent(textwrap.dedent(stripped), "    ")
    return f"{problem_prompt.rstrip()}\n{body}"


def _signature_line(problem_prompt: str) -> str | None:
    for line in problem_prompt.splitlines():
        if _FUNCTION_NAME.match(line) and line.rstrip().endswith(":"):
            return line.strip()
    return None


def _function_name(signature: str) -> str:
    match = _FUNCTION_NAME.match(signature)
    if match is None:  # pragma: no cover - guarded by _signature_line.
        raise ValueError("Expected a Python function signature")
    return match.group("name")


def _is_parseable(code: str) -> bool:
    if not code:
        return False
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError:
        return False
    return True
