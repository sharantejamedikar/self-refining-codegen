"""Three-problem mock integration test for the full refinement loop."""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from data.schema import Problem
from execution import SubprocessExecutor
from feedback import (
    HybridFeedbackGenerator,
    TemplateFeedbackGenerator,
    TraceFeedbackGenerator,
)
from generation import GenerationOutput, GenerationRequest, Generator
from generation.prompts import build_prompt
from loop import RefinementRunner
from utils.config import (
    AppConfig,
    DatasetConfig,
    DeviceConfig,
    ExecutionConfig,
    ExperimentConfig,
    ModelConfig,
)


class FeedbackAwareMockGenerator(Generator):
    """Explicit test mock that fixes one task after receiving feedback."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        """Return canned code selected by prompt and refinement stage."""

        self.prompts.append(request.problem_prompt)
        index = int(request.problem_prompt.rsplit(" ", maxsplit=1)[-1])
        if index == 0 or (index == 1 and request.feedback is not None):
            code = f"def value(): return {index}"
        else:
            code = "def value(): return 99"
        rendered = build_prompt(
            request.problem_prompt,
            previous_code=request.previous_code,
            feedback=request.feedback,
        )
        return GenerationOutput(
            code=code,
            raw_text=code,
            rendered_system_prompt=rendered.system,
            rendered_user_prompt=rendered.user,
            request_payload={
                "system": rendered.system,
                "prompt": rendered.user,
                "feedback": request.feedback,
            },
        )


class RegressingFixedModeMockGenerator(Generator):
    """Pass once, then regress, to exercise fixed-mode aggregation."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        self.calls += 1
        value = 0 if self.calls == 1 else 99
        code = f"def value(): return {value}"
        rendered = build_prompt(
            request.problem_prompt,
            previous_code=request.previous_code,
            feedback=request.feedback,
        )
        return GenerationOutput(
            code=code,
            raw_text=code,
            rendered_system_prompt=rendered.system,
            rendered_user_prompt=rendered.user,
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
        experiment=ExperimentConfig(
            "refinement-integration", 123, str(output_dir), 5, 2, 3
        ),
        device=DeviceConfig("mac", "cpu"),
    )


@pytest.mark.parametrize(
    "feedback_generator",
    [
        TemplateFeedbackGenerator(),
        TraceFeedbackGenerator(),
        HybridFeedbackGenerator(),
    ],
    ids=["template", "trace", "hybrid"],
)
def test_three_problem_full_refinement_integration(
    tmp_path: Path,
    feedback_generator: (
        TemplateFeedbackGenerator | TraceFeedbackGenerator | HybridFeedbackGenerator
    ),
) -> None:
    destination = RefinementRunner(
        FeedbackAwareMockGenerator(),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None, collect_trace=True),
        feedback_generator,
        _config(tmp_path),
    ).run(_problems(), tmp_path / "refinement-run")
    records = {
        path.stem: json.loads(path.read_text())
        for path in (destination / "problems").glob("*.json")
    }
    assert records["Integration_0"]["passed"]
    assert len(records["Integration_0"]["iterations"]) == 1
    assert records["Integration_1"]["passed"]
    assert len(records["Integration_1"]["iterations"]) == 2
    assert not records["Integration_2"]["passed"]
    assert records["Integration_2"]["convergence_reason"] == "oscillation"
    assert records["Integration_2"]["iterations"][0]["feedback"]
    assert records["Integration_2"]["iterations"][0]["feedback_strategy"] in {
        "template",
        "trace",
    }
    persisted_request = records["Integration_1"]["iterations"][1]["generation"][
        "request_payload"
    ]
    assert "Python code generation system" in persisted_request["system"]
    assert persisted_request["feedback"] is not None
    persisted_generation = records["Integration_1"]["iterations"][1]["generation"]
    assert persisted_generation["rendered_system_prompt"] == persisted_request["system"]
    assert persisted_generation["rendered_user_prompt"] == persisted_request["prompt"]
    assert "Execution feedback:" in persisted_generation["rendered_user_prompt"]
    with (destination / "summary.csv").open(newline="") as handle:
        summary = next(csv.DictReader(handle))
    assert summary["metric"] == "pass@1_refined"
    assert summary["solved"] == "2" and summary["total"] == "3"
    diagnostic = json.loads((destination / "run_summary.json").read_text())
    assert diagnostic["convergence_reasons"] == {"oscillation": 1, "success": 2}


def test_fixed_mode_runs_all_five_iterations_and_preserves_any_success(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    config = AppConfig(
        model=config.model,
        dataset=config.dataset,
        execution=config.execution,
        experiment=ExperimentConfig(
            name=config.experiment.name,
            seed=config.experiment.seed,
            output_dir=config.experiment.output_dir,
            max_iterations=5,
            convergence_mode="fixed",
        ),
        device=config.device,
    )
    generator = RegressingFixedModeMockGenerator()
    destination = RefinementRunner(
        generator,
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        TemplateFeedbackGenerator(),
        config,
    ).run([_problems()[0]], tmp_path / "fixed-run")

    record = json.loads((destination / "problems" / "Integration_0.json").read_text())
    assert len(record["iterations"]) == 5
    assert generator.calls == 5
    assert record["passed"] is True
    assert record["iterations"][-1]["classification"]["category"] != "success"
    assert record["convergence_reason"] == "fixed_iterations_complete"
    assert [item["convergence_decision"] for item in record["iterations"]] == [
        "continue",
        "continue",
        "continue",
        "continue",
        "fixed_iterations_complete",
    ]


def test_refinement_resumes_and_skips_complete_records(tmp_path: Path) -> None:
    destination = tmp_path / "refinement-resume"
    problems = _problems()
    RefinementRunner(
        FeedbackAwareMockGenerator(),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        TemplateFeedbackGenerator(),
        _config(tmp_path),
    ).run(problems[:1], destination)

    resumed_generator = FeedbackAwareMockGenerator()
    resumed = RefinementRunner(
        resumed_generator,
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        TemplateFeedbackGenerator(),
        _config(tmp_path),
    ).run(problems, destination)

    assert resumed == destination
    assert problems[0].prompt not in resumed_generator.prompts
    assert len(list((destination / "problems").glob("*.json"))) == 3
    with (destination / "summary.csv").open(newline="") as handle:
        summary = next(csv.DictReader(handle))
    assert summary["total"] == "3"


def test_refinement_resume_rejects_config_mismatch(tmp_path: Path) -> None:
    destination = tmp_path / "refinement-mismatch"
    config = _config(tmp_path)
    RefinementRunner(
        FeedbackAwareMockGenerator(),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        TemplateFeedbackGenerator(),
        config,
    ).run(_problems()[:1], destination)
    changed = replace(config, experiment=replace(config.experiment, seed=7))

    with pytest.raises(ValueError, match="does not match"):
        RefinementRunner(
            FeedbackAwareMockGenerator(),
            SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
            TemplateFeedbackGenerator(),
            changed,
        ).run(_problems(), destination)
