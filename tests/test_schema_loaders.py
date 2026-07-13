"""Tests for unified schema and source dataset loaders."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from data.humaneval import (
    AtomicSplitReport,
    HarnessSplitFailure,
    HumanEvalAtomicSplitError,
    split_humaneval_harness,
    write_atomic_split_report,
)
from data.loaders import (
    download_file,
    load_humaneval,
    load_humaneval_with_report,
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
        "test": (
            "def check(candidate):\n"
            "    assert candidate(1, 2) == 3\n"
            "    assert candidate(-1, 1) == 0"
        ),
        "entry_point": "add",
    }
    with gzip.open(source, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    problems = load_humaneval(source)
    assert problems[0].canonical_solution == "def add(a, b):\n    return a + b\n"
    assert len(problems[0].test_cases) == 2
    assert all(case.endswith("check(add)") for case in problems[0].test_cases)
    assert "candidate(1, 2)" in problems[0].test_cases[0]
    assert "candidate(-1, 1)" in problems[0].test_cases[1]
    assert problems[0].tags == ("humaneval", "atomic-assertions")
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
    assert "Required function signature:\ndef value():" in problem.prompt
    assert all(case.startswith("import math\n") for case in problem.test_cases)


def test_mbpp_loader_rejects_missing_tested_entry_point(tmp_path: Path) -> None:
    source = tmp_path / "mbpp.json"
    source.write_text(
        json.dumps(
            [
                {
                    "task_id": 9,
                    "prompt": "Return one.",
                    "code": "def answer(): return 1",
                    "test_imports": [],
                    "test_list": ["assert missing() == 1"],
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exactly one tested top-level function"):
        load_mbpp_sanitized(source)


def test_humaneval_split_preserves_imports_helpers_metadata_and_entry_point() -> None:
    harness = """
import math
METADATA = {"source": "fixture"}

def approximately_equal(value, expected):
    return math.isclose(value, expected)

def check(candidate):
    assert approximately_equal(candidate(1), 1.5)
    assert approximately_equal(candidate(2), 2.5)
"""
    tests = split_humaneval_harness(harness, "solve")
    assert len(tests) == 2
    assert all("import math" in test for test in tests)
    assert all("METADATA" in test for test in tests)
    assert all("def approximately_equal" in test for test in tests)
    assert all(test.endswith("check(solve)") for test in tests)


@pytest.mark.parametrize(
    ("harness", "reason"),
    [
        (
            "CASES = []\ndef check(candidate):\n    assert candidate(CASES)",
            "shared mutable",
        ),
        (
            "CASES = ([1],)\ndef check(candidate):\n    assert candidate(CASES)",
            "shared mutable",
        ),
        (
            "def check(candidate):\n    value = candidate(1)\n    assert value == 1",
            "non-assert",
        ),
        (
            "import random\ndef check(candidate):\n"
            "    assert candidate(random.randint(1, 10))",
            "dynamic data",
        ),
        (
            "print('setup')\ndef check(candidate):\n    assert candidate(1)",
            "module-level",
        ),
    ],
)
def test_humaneval_split_fails_loudly_for_unsafe_harnesses(
    harness: str, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        split_humaneval_harness(harness, "solve")


def test_humaneval_loader_reports_all_split_failures(tmp_path: Path) -> None:
    source = tmp_path / "humaneval.jsonl.gz"
    safe = {
        "task_id": "HumanEval/safe",
        "prompt": "def solve(x):\n",
        "canonical_solution": "    return x\n",
        "test": "def check(candidate):\n    assert candidate(1) == 1",
        "entry_point": "solve",
    }
    unsafe = {
        **safe,
        "task_id": "HumanEval/unsafe",
        "test": (
            "def check(candidate):\n"
            "    value = candidate(1)\n"
            "    assert value == 1"
        ),
    }
    with gzip.open(source, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(safe) + "\n")
        handle.write(json.dumps(unsafe) + "\n")

    problems, report = load_humaneval_with_report(source)
    assert len(problems) == 1
    assert report.to_dict() == {
        "total_harnesses": 2,
        "atomically_split": 1,
        "failed": 1,
        "total_assertions": 1,
        "failures": [
            {
                "task_id": "HumanEval/unsafe",
                "reason": "check() contains non-assert statements: ['Assign']",
            }
        ],
    }
    with pytest.raises(HumanEvalAtomicSplitError) as error:
        load_humaneval(source)
    assert error.value.report == report


def test_write_atomic_split_report_creates_parent_and_stable_json(
    tmp_path: Path,
) -> None:
    report = AtomicSplitReport(
        total_harnesses=2,
        atomically_split=1,
        failed=1,
        total_assertions=3,
        failures=(HarnessSplitFailure("HumanEval/unsafe", "unsafe fixture"),),
    )
    destination = write_atomic_split_report(
        report, tmp_path / "docs" / "validation" / "report.json"
    )
    assert json.loads(destination.read_text(encoding="utf-8")) == report.to_dict()
    assert destination.read_text(encoding="utf-8").endswith("\n")


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
