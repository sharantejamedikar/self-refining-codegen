"""Tests for the mock generator and single-pass runner."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from data.schema import Problem
from execution import SubprocessExecutor
from generation import GenerationRequest, MockGenerator
from loop import SinglePassRunner
from utils.config import (
    AppConfig,
    DatasetConfig,
    DeviceConfig,
    ExecutionConfig,
    ExperimentConfig,
    ModelConfig,
)


def _problems() -> list[Problem]:
    return [
        Problem(
            f"Integration/{index}",
            f"write value {index}",
            f"def value(): return {index}",
            (f"assert value() == {index}",),
            "fixture",
            ("integration",),
        )
        for index in range(3)
    ]


def _config(output_dir: Path) -> AppConfig:
    return AppConfig(
        model=ModelConfig("mock", "mock", "fixture-v1"),
        dataset=DatasetConfig("fixture", "https://example.invalid"),
        execution=ExecutionConfig(timeout_seconds=1, memory_limit_mb=None),
        experiment=ExperimentConfig("integration", 123, str(output_dir)),
        device=DeviceConfig("mac", "cpu"),
    )


def test_mock_generator_modes_and_missing_prompt() -> None:
    problems = _problems()
    first = GenerationRequest(problems[0].prompt, 1)
    assert "return 0" in MockGenerator.canned_correct(problems).generate(first).code
    assert "AssertionError" in MockGenerator.canned_buggy(problems).generate(first).code
    missing = GenerationRequest("missing", 1)
    assert MockGenerator({}, default_output="x = 1").generate(missing).code == "x = 1"
    with pytest.raises(KeyError, match="No canned"):
        MockGenerator({}).generate(missing)


def test_three_problem_mock_integration(tmp_path: Path) -> None:
    """Run three problems through generate -> sandbox execute -> persisted JSON."""

    problems = _problems()
    runner = SinglePassRunner(
        MockGenerator.canned_correct(problems),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        _config(tmp_path / "runs"),
    )
    destination = runner.run(problems, tmp_path / "integration-run")
    result_files = sorted((destination / "problems").glob("*.json"))
    assert len(result_files) == 3
    assert all(json.loads(path.read_text())["passed"] for path in result_files)
    assert json.loads(result_files[0].read_text())["provenance"] == {
        "backend": "mock",
        "canonical_model": "mock",
        "quantization": None,
        "result_precision": "FULL_PRECISION",
        "revision": "fixture-v1",
    }
    persisted_generation = json.loads(result_files[0].read_text())["iterations"][0][
        "generation"
    ]
    assert (
        "Python code generation system"
        in persisted_generation["rendered_system_prompt"]
    )
    assert problems[0].prompt in persisted_generation["rendered_user_prompt"]
    assert (destination / "config.yaml").exists()
    assert json.loads((destination / "seeds.json").read_text()) == {
        "generation_seed": 123
    }
    with (destination / "summary.csv").open(newline="") as handle:
        summary = next(csv.DictReader(handle))
    assert summary["metric"] == "pass@1_single"
    assert summary["value"] == "1.0"


def test_runner_rejects_empty_problem_list(tmp_path: Path) -> None:
    runner = SinglePassRunner(
        MockGenerator({}),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        _config(tmp_path),
    )
    with pytest.raises(ValueError, match="At least one"):
        runner.run([])
