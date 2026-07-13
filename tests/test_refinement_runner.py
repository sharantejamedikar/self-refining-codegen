"""Three-problem mock integration test for the full refinement loop."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from data.schema import Problem
from execution import SubprocessExecutor
from feedback import TemplateFeedbackGenerator
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

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        """Return canned code selected by prompt and refinement stage."""

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


def test_three_problem_full_refinement_integration(tmp_path: Path) -> None:
    destination = RefinementRunner(
        FeedbackAwareMockGenerator(),
        SubprocessExecutor(timeout_seconds=1, memory_limit_mb=None),
        TemplateFeedbackGenerator(),
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
