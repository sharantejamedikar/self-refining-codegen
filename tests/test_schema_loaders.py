"""Tests for unified schema and source dataset loaders."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from data.loaders import (
    download_file,
    load_humaneval,
    load_jsonl,
    load_mbpp_sanitized,
    write_jsonl,
)
from data.schema import Problem


def test_problem_round_trip_and_exact_fields() -> None:
    problem = Problem("X/1", "prompt", "x = 1", ("assert x == 1",), "easy", ("unit",))
    assert Problem.from_dict(problem.to_dict()) == problem
    with pytest.raises(ValueError, match="exactly"):
        Problem.from_dict({"task_id": "X/1"})


def test_humaneval_loader_and_jsonl_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "humaneval.jsonl.gz"
    record = {
        "task_id": "HumanEval/0",
        "prompt": "def add(a, b):\n",
        "canonical_solution": "    return a + b\n",
        "test": "def check(candidate):\n    assert candidate(1, 2) == 3",
        "entry_point": "add",
    }
    with gzip.open(source, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    problems = load_humaneval(source)
    assert problems[0].canonical_solution == "def add(a, b):\n    return a + b\n"
    assert problems[0].test_cases[0].endswith("check(add)")
    normalized = write_jsonl(problems, tmp_path / "normalized.jsonl")
    assert load_jsonl(normalized) == problems


def test_mbpp_loader_repeats_imports_for_each_test(tmp_path: Path) -> None:
    source = tmp_path / "mbpp.json"
    source.write_text(
        json.dumps(
            [
                {
                    "task_id": 2,
                    "prompt": "Return pi.",
                    "code": "def value(): return math.pi",
                    "test_imports": ["import math"],
                    "test_list": ["assert value() > 3"],
                    "challenge_test_list": ["assert value() < 4"],
                }
            ]
        ),
        encoding="utf-8",
    )
    problem = load_mbpp_sanitized(source)[0]
    assert problem.task_id == "MBPP/2"
    assert problem.tags == ("mbpp", "sanitized")
    assert all(case.startswith("import math\n") for case in problem.test_cases)


def test_loaders_reject_missing_or_wrong_shapes(tmp_path: Path) -> None:
    human = tmp_path / "human.gz"
    with gzip.open(human, "wt", encoding="utf-8") as handle:
        handle.write('{"task_id": "broken"}\n')
    with pytest.raises(ValueError, match="missing"):
        load_humaneval(human)

    mbpp = tmp_path / "mbpp.json"
    mbpp.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="root"):
        load_mbpp_sanitized(mbpp)


def test_download_file_downloads_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"fixture"

    def fake_open(*args: object, **kwargs: object) -> Response:
        nonlocal calls
        calls += 1
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    destination = tmp_path / "nested" / "file.bin"
    assert (
        download_file("https://example.invalid/file", destination).read_bytes()
        == b"fixture"
    )
    download_file("https://example.invalid/file", destination)
    assert calls == 1
