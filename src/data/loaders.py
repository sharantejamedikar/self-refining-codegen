"""Download, normalize, and persist HumanEval and sanitized MBPP."""

from __future__ import annotations

import ast
import gzip
import json
import logging
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from data.humaneval import (
    AtomicSplitReport,
    HarnessSplitFailure,
    HumanEvalAtomicSplitError,
    UnsafeHumanEvalHarnessError,
    split_humaneval_harness,
)
from data.schema import Problem

LOGGER = logging.getLogger(__name__)

HUMANEVAL_URL = (
    "https://raw.githubusercontent.com/openai/human-eval/master/data/"
    "HumanEval.jsonl.gz"
)
MBPP_SANITIZED_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/master/"
    "mbpp/sanitized-mbpp.json"
)


def download_file(url: str, destination: str | Path) -> Path:
    """Download a benchmark artifact unless the destination already exists."""

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    request = urllib.request.Request(
        url, headers={"User-Agent": "self-refining-codegen/0.1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        content = response.read()
    path.write_bytes(content)
    return path


def load_humaneval(path: str | Path) -> list[Problem]:
    """Load HumanEval with strict atomic tests, raising if any harness is unsafe."""

    problems, report = load_humaneval_with_report(path)
    if report.failed:
        raise HumanEvalAtomicSplitError(report)
    return problems


def load_humaneval_with_report(
    path: str | Path,
) -> tuple[list[Problem], AtomicSplitReport]:
    """Normalize safe harnesses and return an explicit split/failure report."""

    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    problems: list[Problem] = []
    failures: list[HarnessSplitFailure] = []
    assertion_count = 0
    for record in records:
        task_id = str(record.get("task_id", "<missing-task-id>"))
        try:
            problem = _normalize_humaneval(record)
        except UnsafeHumanEvalHarnessError as error:
            failures.append(HarnessSplitFailure(task_id, str(error)))
            LOGGER.error("HumanEval atomic split failed for %s: %s", task_id, error)
        else:
            problems.append(problem)
            assertion_count += len(problem.test_cases)
    report = AtomicSplitReport(
        total_harnesses=len(records),
        atomically_split=len(problems),
        failed=len(failures),
        total_assertions=assertion_count,
        failures=tuple(failures),
    )
    LOGGER.info(
        "HumanEval atomic split: %d/%d split, %d/%d failed, %d assertions",
        report.atomically_split,
        report.total_harnesses,
        report.failed,
        report.total_harnesses,
        report.total_assertions,
    )
    return problems, report


def load_mbpp_sanitized(path: str | Path) -> list[Problem]:
    """Load the official sanitized MBPP JSON and normalize it."""

    with Path(path).open(encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise ValueError("Sanitized MBPP root must be a list")
    return [_normalize_mbpp(record) for record in records]


def write_jsonl(problems: Iterable[Problem], path: str | Path) -> Path:
    """Write normalized problems as deterministic UTF-8 JSON Lines."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for problem in problems:
            handle.write(json.dumps(problem.to_dict(), sort_keys=True) + "\n")
    return destination


def load_jsonl(path: str | Path) -> list[Problem]:
    """Load problems and enforce benchmark-specific normalized invariants."""

    with Path(path).open(encoding="utf-8") as handle:
        problems = [
            Problem.from_dict(json.loads(line)) for line in handle if line.strip()
        ]
    for problem in problems:
        if {"mbpp", "sanitized"}.issubset(problem.tags):
            _validate_normalized_mbpp_prompt(problem)
    return problems


def _normalize_humaneval(record: dict[str, Any]) -> Problem:
    required = {"task_id", "prompt", "canonical_solution", "test", "entry_point"}
    missing = required - set(record)
    if missing:
        raise ValueError(f"HumanEval record is missing {sorted(missing)}")
    code = f"{record['prompt']}{record['canonical_solution']}"
    tests = split_humaneval_harness(str(record["test"]), str(record["entry_point"]))
    return Problem(
        task_id=str(record["task_id"]),
        prompt=str(record["prompt"]),
        canonical_solution=code,
        test_cases=tests,
        difficulty="unspecified",
        tags=("humaneval", "atomic-assertions"),
    )


def _normalize_mbpp(record: dict[str, Any]) -> Problem:
    required = {"task_id", "prompt", "code", "test_list"}
    missing = required - set(record)
    if missing:
        raise ValueError(f"Sanitized MBPP record is missing {sorted(missing)}")
    imports = [str(item) for item in record.get("test_imports", [])]
    assertions = [str(item) for item in record["test_list"]]
    assertions += [str(item) for item in record.get("challenge_test_list", [])]
    tests = ["\n".join([*imports, assertion]) for assertion in assertions]
    signature = _extract_mbpp_entry_point_signature(
        str(record["code"]), assertions, str(record["task_id"])
    )
    prompt = (
        f"{str(record['prompt']).rstrip()}\n\n"
        f"Required function signature:\n{signature}"
    )
    return Problem(
        task_id=f"MBPP/{record['task_id']}",
        prompt=prompt,
        canonical_solution=str(record["code"]),
        test_cases=tuple(tests),
        difficulty="unspecified",
        tags=("mbpp", "sanitized"),
    )


def _extract_mbpp_entry_point_signature(
    canonical_solution: str, assertions: list[str], task_id: str
) -> str:
    """Derive one tested top-level function signature from sanitized MBPP fields."""

    solution_tree = ast.parse(canonical_solution)
    functions = {
        node.name: node
        for node in solution_tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    called_names = {
        node.func.id
        for assertion in assertions
        for node in ast.walk(ast.parse(assertion))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    entry_points = sorted(functions.keys() & called_names)
    if len(entry_points) != 1:
        raise ValueError(
            f"MBPP task {task_id} must have exactly one tested top-level function; "
            f"found {entry_points}"
        )
    function = functions[entry_points[0]]
    prefix = "async def" if isinstance(function, ast.AsyncFunctionDef) else "def"
    return_annotation = (
        f" -> {ast.unparse(function.returns)}" if function.returns is not None else ""
    )
    return (
        f"{prefix} {function.name}({ast.unparse(function.args)})"
        f"{return_annotation}:"
    )


def _validate_normalized_mbpp_prompt(problem: Problem) -> None:
    """Reject stale normalized MBPP records without the tested entry point."""

    marker = "Required function signature:"
    signature = _extract_mbpp_entry_point_signature(
        problem.canonical_solution, list(problem.test_cases), problem.task_id
    )
    required_block = f"{marker}\n{signature}"
    if problem.prompt.count(marker) != 1 or required_block not in problem.prompt:
        raise ValueError(
            f"Normalized MBPP task {problem.task_id} must contain exactly one "
            f"tested signature block: {required_block!r}"
        )
