"""Config-driven iterative generation, execution, and feedback orchestration."""

from __future__ import annotations

import csv
import json
import subprocess
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from convergence import (
    ConvergenceDetector,
    ConvergenceReason,
    IterationRecord,
    stable_hash,
)
from data.schema import Problem
from execution.base import ExecutionResult, Executor
from feedback import FeedbackGenerator, classify_execution
from generation.base import GenerationRequest, Generator
from loop.persistence import model_provenance, write_problem_record
from utils.config import AppConfig


class RefinementRunner:
    """Refine candidates until success or deterministic convergence."""

    def __init__(
        self,
        generator: Generator,
        executor: Executor,
        feedback_generator: FeedbackGenerator,
        config: AppConfig,
    ) -> None:
        self.generator = generator
        self.executor = executor
        self.feedback_generator = feedback_generator
        self.config = config
        experiment = config.experiment
        self.detector = ConvergenceDetector(
            experiment.max_iterations,
            experiment.stagnation_patience,
            experiment.oscillation_window,
        )

    def run(
        self, problems: Iterable[Problem], run_dir: str | Path | None = None
    ) -> Path:
        """Run refinement and persist reproducible per-problem records."""

        problem_list = list(problems)
        if not problem_list:
            raise ValueError("At least one problem is required")
        destination = Path(run_dir) if run_dir else self._new_run_directory()
        self._write_run_metadata(destination)
        problem_dir = destination / "problems"
        problem_dir.mkdir()
        records: list[dict[str, Any]] = []
        for problem in problem_list:
            record = self._run_problem(problem)
            write_problem_record(problem_dir, record)
            records.append(record)
        self._write_summary(destination, records)
        return destination

    def _run_problem(self, problem: Problem) -> dict[str, Any]:
        started = time.monotonic()
        iterations: list[dict[str, Any]] = []
        convergence_records: list[IterationRecord] = []
        previous_code: str | None = None
        feedback: str | None = None
        first_generation = None

        for iteration in range(1, self.config.experiment.max_iterations + 1):
            generation_started = time.monotonic()
            generated = self.generator.generate(
                GenerationRequest(
                    problem_prompt=problem.prompt,
                    seed=self.config.experiment.seed,
                    previous_code=previous_code,
                    feedback=feedback,
                )
            )
            if first_generation is None:
                first_generation = generated
            generation_duration = time.monotonic() - generation_started
            execution = self.executor.execute(generated.code, list(problem.test_cases))
            classification = classify_execution(execution)
            rendered_feedback = self.feedback_generator.generate(
                classification, execution
            )
            convergence_records.append(
                IterationRecord(
                    iteration=iteration,
                    code_hash=stable_hash(generated.code),
                    passed_assertions=classification.passed_assertions,
                    total_assertions=classification.total_assertions,
                    error_hash=self._error_hash(execution),
                    success=classification.category.value == "success",
                )
            )
            if self.config.experiment.convergence_mode == "fixed":
                decision = (
                    ConvergenceReason.FIXED_ITERATIONS_COMPLETE
                    if iteration == self.config.experiment.max_iterations
                    else ConvergenceReason.CONTINUE
                )
            else:
                decision = self.detector.decide(convergence_records)
            iterations.append(
                {
                    "iteration": iteration,
                    "seed": self.config.experiment.seed,
                    "generation": generated.to_dict(),
                    "execution": execution.to_dict(),
                    "classification": {
                        "category": classification.category.value,
                        "passed_assertions": classification.passed_assertions,
                        "total_assertions": classification.total_assertions,
                        "assertion_pass_rate_diagnostic": classification.pass_rate,
                    },
                    "feedback": rendered_feedback,
                    "feedback_strategy": self.feedback_generator.strategy_for(
                        classification, execution
                    ),
                    "convergence_decision": decision.value,
                    "convergence_state": asdict(convergence_records[-1]),
                    "timing": {
                        "generation_seconds": generation_duration,
                        "execution_seconds": execution.duration_seconds,
                    },
                }
            )
            if decision is not ConvergenceReason.CONTINUE:
                break
            previous_code = generated.code
            feedback = rendered_feedback

        if first_generation is None:
            raise AssertionError("max_iterations must be positive")
        return {
            "task_id": problem.task_id,
            "seed": self.config.experiment.seed,
            "passed": any(
                item["classification"]["category"] == "success" for item in iterations
            ),
            "metric": "pass@1_refined",
            "provenance": model_provenance(self.config.model, first_generation),
            "iterations": iterations,
            "convergence_reason": iterations[-1]["convergence_decision"],
            "duration_seconds": time.monotonic() - started,
        }

    @staticmethod
    def _error_hash(execution: ExecutionResult) -> str:
        failures = [
            {
                "type": test.exception_type,
                "message": test.exception_message,
                "timed_out": test.timed_out,
            }
            for test in execution.tests
            if not test.passed
        ]
        return stable_hash(json.dumps(failures, sort_keys=True))

    def _new_run_directory(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        return (
            Path(self.config.experiment.output_dir)
            / f"{timestamp}_{self.config.experiment.name}"
        )

    def _write_run_metadata(self, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "config.yaml").write_text(
            yaml.safe_dump(asdict(self.config), sort_keys=True), encoding="utf-8"
        )
        (destination / "seeds.json").write_text(
            json.dumps({"generation_seed": self.config.experiment.seed}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
        commit = (
            completed.stdout.strip() if completed.returncode == 0 else "unavailable"
        )
        (destination / "git_commit.txt").write_text(commit + "\n", encoding="utf-8")

    @staticmethod
    def _write_summary(destination: Path, records: list[dict[str, Any]]) -> None:
        solved = sum(bool(record["passed"]) for record in records)
        iterations = [item for record in records for item in record["iterations"]]
        prompt_tokens = sum(
            int(item["generation"]["prompt_tokens"] or 0) for item in iterations
        )
        completion_tokens = sum(
            int(item["generation"]["completion_tokens"] or 0) for item in iterations
        )
        total_duration = sum(float(record["duration_seconds"]) for record in records)
        with (destination / "summary.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "metric",
                    "solved",
                    "total",
                    "value",
                    "wall_clock_seconds",
                    "prompt_tokens",
                    "completion_tokens",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "metric": "pass@1_refined",
                    "solved": solved,
                    "total": len(records),
                    "value": solved / len(records),
                    "wall_clock_seconds": total_duration,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
            )

        transitions: Counter[str] = Counter()
        for record in records:
            categories = [
                item["classification"]["category"] for item in record["iterations"]
            ]
            transitions.update(
                f"{first}->{second}"
                for first, second in zip(categories, categories[1:], strict=False)
            )
        diagnostics = {
            "metric": "pass@1_refined",
            "solved": solved,
            "total": len(records),
            "value": solved / len(records),
            "iterations_to_success": dict(
                Counter(
                    str(len(record["iterations"]))
                    for record in records
                    if record["passed"]
                )
            ),
            "convergence_reasons": dict(
                Counter(record["convergence_reason"] for record in records)
            ),
            "error_category_transitions": dict(transitions),
            "wall_clock_seconds": total_duration,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        (destination / "run_summary.json").write_text(
            json.dumps(diagnostics, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
