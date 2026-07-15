"""Config-driven single-pass generation and execution runner."""

from __future__ import annotations

import csv
import json
import subprocess
import time
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from data.schema import Problem
from execution.base import Executor
from generation.base import GenerationRequest, Generator
from loop.persistence import write_problem_record
from utils.config import AppConfig


class SinglePassRunner:
    """Generate and sandbox-execute one candidate per problem."""

    def __init__(
        self, generator: Generator, executor: Executor, config: AppConfig
    ) -> None:
        self.generator = generator
        self.executor = executor
        self.config = config

    def run(
        self, problems: Iterable[Problem], run_dir: str | Path | None = None
    ) -> Path:
        """Run all problems and persist a reproducible result directory."""

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
        generation_started = time.monotonic()
        generated = self.generator.generate(
            GenerationRequest(
                problem_prompt=problem.prompt, seed=self.config.experiment.seed
            )
        )
        generation_duration = time.monotonic() - generation_started
        execution = self.executor.execute(generated.code, list(problem.test_cases))
        return {
            "task_id": problem.task_id,
            "seed": self.config.experiment.seed,
            "passed": execution.passed,
            "metric": "pass@1_single",
            "iterations": [
                {
                    "iteration": 1,
                    "generation": generated.to_dict(),
                    "execution": execution.to_dict(),
                    "feedback": None,
                    "convergence_decision": "single_pass_complete",
                    "timing": {
                        "generation_seconds": generation_duration,
                        "execution_seconds": execution.duration_seconds,
                    },
                }
            ],
            "duration_seconds": time.monotonic() - started,
        }

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
        (destination / "git_commit.txt").write_text(
            self._git_commit() + "\n", encoding="utf-8"
        )

    @staticmethod
    def _git_commit() -> str:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
        return completed.stdout.strip() if completed.returncode == 0 else "unavailable"

    @staticmethod
    def _write_summary(destination: Path, records: list[dict[str, Any]]) -> None:
        solved = sum(bool(record["passed"]) for record in records)
        total_duration = sum(float(record["duration_seconds"]) for record in records)
        prompt_tokens = sum(
            int(record["iterations"][0]["generation"]["prompt_tokens"] or 0)
            for record in records
        )
        completion_tokens = sum(
            int(record["iterations"][0]["generation"]["completion_tokens"] or 0)
            for record in records
        )
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
                    "metric": "pass@1_single",
                    "solved": solved,
                    "total": len(records),
                    "value": solved / len(records),
                    "wall_clock_seconds": total_duration,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                }
            )
