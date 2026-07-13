"""Download, normalize, and persist HumanEval and sanitized MBPP."""

from __future__ import annotations

import gzip
import json
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from data.schema import Problem

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
    request = urllib.request.Request(url, headers={"User-Agent": "self-refining-codegen/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        content = response.read()
    path.write_bytes(content)
    return path


def load_humaneval(path: str | Path) -> list[Problem]:
    """Load official HumanEval JSONL.GZ and normalize it."""

    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    return [_normalize_humaneval(record) for record in records]


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
    """Load problems from the unified JSON Lines format."""

    with Path(path).open(encoding="utf-8") as handle:
        return [Problem.from_dict(json.loads(line)) for line in handle if line.strip()]


def _normalize_humaneval(record: dict[str, Any]) -> Problem:
    required = {"task_id", "prompt", "canonical_solution", "test", "entry_point"}
    missing = required - set(record)
    if missing:
        raise ValueError(f"HumanEval record is missing {sorted(missing)}")
    code = f"{record['prompt']}{record['canonical_solution']}"
    test = f"{record['test']}\ncheck({record['entry_point']})"
    return Problem(
        task_id=str(record["task_id"]),
        prompt=str(record["prompt"]),
        canonical_solution=code,
        test_cases=(test,),
        difficulty="unspecified",
        tags=("humaneval",),
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
    return Problem(
        task_id=f"MBPP/{record['task_id']}",
        prompt=str(record["prompt"]),
        canonical_solution=str(record["code"]),
        test_cases=tuple(tests),
        difficulty="unspecified",
        tags=("mbpp", "sanitized"),
    )
