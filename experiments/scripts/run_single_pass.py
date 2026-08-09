"""Run a configured real-model single-pass development experiment."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from data import load_jsonl
from execution import SubprocessExecutor
from generation import (
    GPUPreflightRefused,
    HuggingFaceGenerator,
    OllamaGenerator,
    create_generator,
)
from loop import SinglePassRunner
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
    """Validate the artifact, load the frozen dev split, and run generation."""

    args = parse_args()
    config = load_config(args.config, args.profile)
    if not config.dataset.path:
        raise ValueError("Real-model runs require dataset.path in config")
    problems = load_jsonl(Path(config.dataset.path))
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        problems = problems[: args.limit]

    generator = create_generator(config.model, config.device.accelerator)
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
    )
    destination = SinglePassRunner(generator, executor, config).run(
        problems, run_dir=args.run_dir
    )
    if isinstance(generator, HuggingFaceGenerator):
        footprint = generator.get_memory_footprint()
        print(
            f"Model memory footprint: {footprint} bytes ({footprint / 2**30:.2f} GiB)"
        )
    print(destination)


if __name__ == "__main__":
    try:
        main()
    except GPUPreflightRefused as error:
        raise SystemExit(f"SAFETY REFUSAL: {error}") from None
