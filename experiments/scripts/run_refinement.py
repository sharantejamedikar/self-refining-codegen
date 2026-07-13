"""Run a configured refinement development experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

from data import load_jsonl
from execution import SubprocessExecutor
from feedback import create_feedback_generator
from generation import OllamaGenerator, create_generator
from loop import RefinementRunner
from utils.config import load_config


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--profile", choices=("mac", "cluster", "colab"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--run-dir")
    return parser.parse_args()


def main() -> None:
    """Verify the model artifact and refine candidates on a dev split."""

    args = parse_args()
    config = load_config(args.config, args.profile)
    if not config.dataset.path:
        raise ValueError("Real-model runs require dataset.path in config")
    problems = load_jsonl(Path(config.dataset.path))
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        problems = problems[: args.limit]
    generator = create_generator(config.model)
    if isinstance(generator, OllamaGenerator):
        artifact = generator.verify_artifact()
        print(
            "Verified Ollama artifact:",
            artifact.get("name", artifact.get("model")),
            artifact.get("digest"),
        )
    executor = SubprocessExecutor(
        timeout_seconds=config.execution.timeout_seconds,
        memory_limit_mb=config.execution.memory_limit_mb,
        python_executable=config.execution.python_executable,
        collect_trace=config.execution.collect_trace,
    )
    destination = RefinementRunner(
        generator,
        executor,
        create_feedback_generator(config.experiment.feedback_strategy),
        config,
    ).run(problems, run_dir=args.run_dir)
    print(destination)


if __name__ == "__main__":
    main()
