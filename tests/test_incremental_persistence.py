"""Tests that completed records survive a later problem failure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data.schema import Problem
from execution import SubprocessExecutor
from feedback import TemplateFeedbackGenerator
from generation import GenerationOutput, GenerationRequest, Generator
from loop import BestOfKRunner, RefinementRunner, SinglePassRunner
from utils.config import (
    AppConfig,
    DatasetConfig,
    DeviceConfig,
    ExecutionConfig,
    ExperimentConfig,
    ModelConfig,
)


class FailOnSecondProblemGenerator(Generator):
    """Return valid canned code once, then simulate a model failure."""

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        if request.problem_prompt == "second":
            raise RuntimeError("simulated model failure")
        code = "def value(): return 1"
        return GenerationOutput(
            code=code,
            raw_text=code,
            rendered_system_prompt="mock system",
            rendered_user_prompt=request.problem_prompt,
        )


def _problems() -> list[Problem]:
    return [
        Problem(
            "Integration/first",
            "first",
            "def value(): return 1",
            ("assert value() == 1",),
            "fixture",
            ("integration",),
        ),
        Problem(
            "Integration/second",
            "second",
            "def value(): return 2",
            ("assert value() == 2",),
            "fixture",
            ("integration",),
        ),
    ]


def _config(output_dir: Path) -> AppConfig:
    return AppConfig(
        model=ModelConfig("mock", "mock", "fixture-v1"),
        dataset=DatasetConfig("fixture", "https://example.invalid"),
        execution=ExecutionConfig(timeout_seconds=1, memory_limit_mb=None),
        experiment=ExperimentConfig(
            name="incremental-test",
            seed=42,
            output_dir=str(output_dir),
            max_iterations=5,
            samples_per_problem=5,
        ),
        device=DeviceConfig("mac", "cpu"),
    )


@pytest.mark.parametrize("runner_kind", ["single", "best_of_k", "refinement"])
def test_completed_problem_is_persisted_before_later_failure(
    tmp_path: Path, runner_kind: str
) -> None:
    config = _config(tmp_path)
    generator = FailOnSecondProblemGenerator()
    executor = SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None)
    if runner_kind == "single":
        runner = SinglePassRunner(generator, executor, config)
    elif runner_kind == "best_of_k":
        runner = BestOfKRunner(generator, executor, config)
    else:
        runner = RefinementRunner(
            generator, executor, TemplateFeedbackGenerator(), config
        )
    destination = tmp_path / runner_kind

    with pytest.raises(RuntimeError, match="simulated model failure"):
        runner.run(_problems(), destination)

    completed = destination / "problems" / "Integration_first.json"
    assert completed.exists()
    assert json.loads(completed.read_text())["task_id"] == "Integration/first"
    assert not (destination / "problems" / "Integration_second.json").exists()
    assert not (destination / "summary.csv").exists()
