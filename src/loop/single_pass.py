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
from loop.persistence import model_provenance, write_problem_record
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
        resuming = destination.exists()
        if resuming:
            self._validate_resume_directory(destination)
        else:
            self._write_run_metadata(destination)
        problem_dir = destination / "problems"
        problem_dir.mkdir(exist_ok=resuming)

        records: list[dict[str, Any]] = []
        for problem in problem_list:
            record = self._load_completed_record(problem_dir, problem)
            if record is None:
                record = self._run_problem(problem)
                write_problem_record(problem_dir, record)
            records.append(record)
        self._write_summary(destination, records)
        return destination

    def _validate_resume_directory(self, destination: Path) -> None:
        """Refuse to mix single-pass records from different configurations."""

        if not destination.is_dir():
            raise ValueError(f"Resume path is not a directory: {destination}")
        config_path = destination / "config.yaml"
        if not config_path.is_file():
            raise ValueError(f"Resume directory has no config snapshot: {destination}")
        with config_path.open(encoding="utf-8") as handle:
            stored_config = yaml.safe_load(handle)
        if stored_config != asdict(self.config):
            raise ValueError("Resume config does not match the stored run config")

    def _load_completed_record(
        self, problem_dir: Path, problem: Problem
    ) -> dict[str, Any] | None:
        """Load a structurally complete record, or regenerate it when incomplete."""

        path = problem_dir / f"{problem.task_id.replace('/', '_')}.json"
        if not path.is_file():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        iterations = record.get("iterations")
        if (
            record.get("task_id") != problem.task_id
            or record.get("metric") != "pass@1_single"
            or record.get("seed") != self.config.experiment.seed
            or not isinstance(record.get("passed"), bool)
            or not isinstance(iterations, list)
            or len(iterations) != 1
            or iterations[0].get("iteration") != 1
            or iterations[0].get("convergence_decision") != "single_pass_complete"
        ):
            return None
        return record

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
            "provenance": model_provenance(self.config.model, generated),
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
