"""Run an M1 dev problem through the mock single-pass pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from data import load_jsonl
from execution import SubprocessExecutor
from generation import MockGenerator
from loop import SinglePassRunner
from utils.config import load_config


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/m1_mock.yaml")
    parser.add_argument("--profile", choices=("mac", "cluster", "colab"), default="mac")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--mode", choices=("correct", "buggy"), default="correct")
    parser.add_argument("--run-dir")
    return parser.parse_args()


def main() -> None:
    """Load the configured dev split and execute it with a canned mock."""

    args = parse_args()
    config = load_config(args.config, args.profile)
    dataset_path = (
        Path(config.dataset.data_dir) / "dev" / f"{config.dataset.name}_dev.jsonl"
    )
    problems = load_jsonl(dataset_path)[: args.limit]
    generator = (
        MockGenerator.canned_correct(problems)
        if args.mode == "correct"
        else MockGenerator.canned_buggy(problems)
    )
    executor = SubprocessExecutor(
        timeout_seconds=config.execution.timeout_seconds,
        memory_limit_mb=config.execution.memory_limit_mb,
        python_executable=config.execution.python_executable,
    )
    destination = SinglePassRunner(generator, executor, config).run(
        problems, run_dir=args.run_dir
    )
    print(destination)


if __name__ == "__main__":
    main()
