"""Compute-matched independent-sampling baseline runner."""

from __future__ import annotations

import csv
import hashlib
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
from utils.config import AppConfig


class BestOfKRunner:
    """Generate and execute k reproducible independent samples per problem."""

    def __init__(
        self, generator: Generator, executor: Executor, config: AppConfig
    ) -> None:
        self.generator = generator
        self.executor = executor
        self.config = config

    def run(
        self, problems: Iterable[Problem], run_dir: str | Path | None = None
    ) -> Path:
        """Run every configured sample and persist reproducible result records."""

        problem_list = list(problems)
        if not problem_list:
            raise ValueError("At least one problem is required")
        destination = Path(run_dir) if run_dir else self._new_run_directory()
        self._write_run_metadata(destination)
        problem_dir = destination / "problems"
        problem_dir.mkdir()

        records = [self._run_problem(problem) for problem in problem_list]
        for record in records:
            filename = str(record["task_id"]).replace("/", "_") + ".json"
            (problem_dir / filename).write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        self._write_summary(destination, records)
        return destination

    def _run_problem(self, problem: Problem) -> dict[str, Any]:
        started = time.monotonic()
        candidates: list[dict[str, Any]] = []
        base_seed = self.config.experiment.seed

        for sample_index in range(self.config.experiment.samples_per_problem):
            seed = base_seed + sample_index
            generation_started = time.monotonic()
            generated = self.generator.generate(
                GenerationRequest(problem_prompt=problem.prompt, seed=seed)
            )
            generation_duration = time.monotonic() - generation_started
            execution = self.executor.execute(generated.code, list(problem.test_cases))
            candidates.append(
                {
                    "sample_index": sample_index,
                    "seed": seed,
                    "code_hash": hashlib.sha256(
                        generated.code.encode("utf-8")
                    ).hexdigest(),
                    "passed": execution.passed,
                    "generation": generated.to_dict(),
                    "execution": execution.to_dict(),
                    "timing": {
                        "generation_seconds": generation_duration,
                        "execution_seconds": execution.duration_seconds,
                    },
                }
            )

        passing_indices = [
            int(candidate["sample_index"])
            for candidate in candidates
            if candidate["passed"]
        ]
        unique_code_count = len({candidate["code_hash"] for candidate in candidates})
        return {
            "task_id": problem.task_id,
            "base_seed": base_seed,
            "sample_seeds": [candidate["seed"] for candidate in candidates],
            "passed": bool(passing_indices),
            "passing_sample_indices": passing_indices,
            "candidate_count": len(candidates),
            "unique_code_count": unique_code_count,
            "all_candidates_unique": unique_code_count == len(candidates),
            "metric": "pass@1_bo5",
            "candidates": candidates,
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
        seeds = [
            self.config.experiment.seed + index
            for index in range(self.config.experiment.samples_per_problem)
        ]
        (destination / "seeds.json").write_text(
            json.dumps(
                {
                    "base_generation_seed": self.config.experiment.seed,
                    "sample_generation_seeds": seeds,
                    "derivation": "base_generation_seed + sample_index",
                },
                indent=2,
            )
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
        candidates = [
            candidate for record in records for candidate in record["candidates"]
        ]
        prompt_tokens = sum(
            int(candidate["generation"]["prompt_tokens"] or 0)
            for candidate in candidates
        )
        completion_tokens = sum(
            int(candidate["generation"]["completion_tokens"] or 0)
            for candidate in candidates
        )
        wall_clock_seconds = sum(
            float(record["duration_seconds"]) for record in records
        )
        fieldnames = [
            "metric",
            "solved",
            "total",
            "value",
            "wall_clock_seconds",
            "prompt_tokens",
            "completion_tokens",
        ]
        row = {
            "metric": "pass@1_bo5",
            "solved": solved,
            "total": len(records),
            "value": solved / len(records),
            "wall_clock_seconds": wall_clock_seconds,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        with (destination / "summary.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)

        diagnostics = {
            **row,
            "candidate_count": len(candidates),
            "samples_per_problem": (len(candidates) // len(records) if records else 0),
            "unique_code_count": sum(
                int(record["unique_code_count"]) for record in records
            ),
            "problems_with_all_unique_candidates": sum(
                bool(record["all_candidates_unique"]) for record in records
            ),
        }
        (destination / "run_summary.json").write_text(
            json.dumps(diagnostics, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
