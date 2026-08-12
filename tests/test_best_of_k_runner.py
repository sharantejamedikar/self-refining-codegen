"""Tests for the compute-matched independent-sampling baseline."""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from data.schema import Problem
from execution import SubprocessExecutor
from generation.base import GenerationOutput, GenerationRequest, Generator
from generation.prompts import build_prompt
from loop import BestOfKRunner
from utils.config import (
    AppConfig,
    DatasetConfig,
    DeviceConfig,
    ExecutionConfig,
    ExperimentConfig,
    ModelConfig,
)


class SeededGenerator(Generator):
    """Return a passing candidate only for selected deterministic seeds."""

    def __init__(self) -> None:
        self.seeds: list[int] = []

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        self.seeds.append(request.seed)
        value = 1 if request.seed == 44 else 0
        code = f"def value(): return {value}"
        rendered = build_prompt(request.problem_prompt)
        return GenerationOutput(
            code=code,
            raw_text=code,
            rendered_system_prompt=rendered.system,
            rendered_user_prompt=rendered.user,
            prompt_tokens=10,
            completion_tokens=3,
            request_payload={"options": {"seed": request.seed}},
        )


def _config(output_dir: Path) -> AppConfig:
    return AppConfig(
        model=ModelConfig("mock", "mock", "fixture-v1", temperature=0.8),
        dataset=DatasetConfig("fixture", "https://example.invalid"),
        execution=ExecutionConfig(timeout_seconds=1, memory_limit_mb=None),
        experiment=ExperimentConfig(
            name="best-of-5",
            seed=42,
            output_dir=str(output_dir),
            samples_per_problem=5,
        ),
        device=DeviceConfig("mac", "cpu"),
    )


def test_best_of_five_runs_every_candidate_and_aggregates(tmp_path: Path) -> None:
    generator = SeededGenerator()
    problem = Problem(
        "Integration/0",
        "def value():\n",
        "def value(): return 1",
        ("assert value() == 1",),
        "fixture",
        ("integration",),
    )
    destination = BestOfKRunner(
        generator,
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        _config(tmp_path),
    ).run([problem], tmp_path / "best-of-5-run")

    assert generator.seeds == [42, 43, 44, 45, 46]
    record = json.loads((destination / "problems" / "Integration_0.json").read_text())
    assert record["passed"] is True
    assert record["passing_sample_indices"] == [2]
    assert len(record["candidates"]) == 5
    assert record["unique_code_count"] == 2
    assert record["provenance"]["result_precision"] == "FULL_PRECISION"
    assert all(
        candidate["generation"]["request_payload"]["options"]["seed"]
        == candidate["seed"]
        for candidate in record["candidates"]
    )
    assert json.loads((destination / "seeds.json").read_text())[
        "sample_generation_seeds"
    ] == [42, 43, 44, 45, 46]
    with (destination / "summary.csv").open(newline="") as handle:
        summary = next(csv.DictReader(handle))
    assert summary["metric"] == "pass@1_bo5"
    assert summary["value"] == "1.0"
    assert summary["prompt_tokens"] == "50"
    assert summary["completion_tokens"] == "15"


def test_best_of_k_rejects_empty_problem_list(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="At least one"):
        BestOfKRunner(
            SeededGenerator(),
            SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
            _config(tmp_path),
        ).run([])


def test_best_of_k_resumes_and_skips_complete_records(tmp_path: Path) -> None:
    problems = [
        Problem(
            f"Integration/{index}",
            "def value():\n",
            "def value(): return 1",
            ("assert value() == 1",),
            "fixture",
            ("integration",),
        )
        for index in range(2)
    ]
    destination = tmp_path / "best-of-5-resume"
    first_generator = SeededGenerator()
    runner = BestOfKRunner(
        first_generator,
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        _config(tmp_path),
    )
    runner.run(problems[:1], destination)

    resumed_generator = SeededGenerator()
    resumed = BestOfKRunner(
        resumed_generator,
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        _config(tmp_path),
    ).run(problems, destination)

    assert resumed == destination
    assert resumed_generator.seeds == [42, 43, 44, 45, 46]
    assert len(list((destination / "problems").glob("*.json"))) == 2
    with (destination / "summary.csv").open(newline="") as handle:
        summary = next(csv.DictReader(handle))
    assert summary["total"] == "2"
    assert summary["prompt_tokens"] == "100"
    assert summary["completion_tokens"] == "30"


def test_best_of_k_resume_rejects_config_mismatch(tmp_path: Path) -> None:
    problem = Problem(
        "Integration/0",
        "def value():\n",
        "def value(): return 1",
        ("assert value() == 1",),
        "fixture",
        ("integration",),
    )
    destination = tmp_path / "best-of-5-mismatch"
    config = _config(tmp_path)
    BestOfKRunner(
        SeededGenerator(),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        config,
    ).run([problem], destination)
    config = replace(config, experiment=replace(config.experiment, seed=7))

    with pytest.raises(ValueError, match="does not match"):
        BestOfKRunner(
            SeededGenerator(),
            SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
            config,
        ).run([problem], destination)
