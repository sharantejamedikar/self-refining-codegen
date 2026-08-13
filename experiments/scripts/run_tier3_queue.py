"""Run an explicit Tier 3 config queue on one guarded physical GPU."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from generation.gpu_safety import GPUPreflightRefused, require_gpu_idle


def parse_args() -> argparse.Namespace:
    """Parse the GPU assignment and ordered config queue."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-index", type=int, required=True)
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("configs", nargs="+", type=Path)
    return parser.parse_args()


def _pid_exists(pid: int) -> bool:
    stat_path = Path(f"/proc/{pid}/stat")
    try:
        fields = stat_path.read_text(encoding="utf-8").split()
    except (FileNotFoundError, PermissionError, OSError):
        fields = []
    if len(fields) >= 3 and fields[2] == "Z":
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _runner(config: Path) -> str:
    name = config.name
    if "best_of_5" in name:
        return "run_best_of_k.py"
    if "hybrid_refinement" in name:
        return "run_refinement.py"
    if "zero_shot" in name:
        return "run_single_pass.py"
    raise ValueError(f"Cannot select runner for {config}")


def _wait_until_idle(gpu_index: int) -> None:
    while True:
        try:
            result = require_gpu_idle(
                gpu_index=gpu_index,
                utilization_threshold_percent=25.0,
                memory_threshold_mb=500.0,
            )
        except GPUPreflightRefused as error:
            print(f"GPU {gpu_index} preflight deferred: {error}", flush=True)
            time.sleep(30)
        else:
            print(f"GPU {gpu_index} preflight passed: {result.to_dict()}", flush=True)
            return


def main() -> None:
    """Wait for the current worker, then run every config in order."""

    args = parse_args()
    if args.wait_pid is not None:
        while _pid_exists(args.wait_pid):
            time.sleep(30)
    environment = dict(os.environ)
    environment["CUDA_VISIBLE_DEVICES"] = str(args.gpu_index)
    environment["PYTHONPATH"] = "src"
    python = sys.executable
    for config in args.configs:
        _wait_until_idle(args.gpu_index)
        command = [
            python,
            f"experiments/scripts/{_runner(config)}",
            "--config",
            str(config),
            "--profile",
            "cluster",
        ]
        print(f"Starting: {' '.join(command)}", flush=True)
        subprocess.run(command, check=True, env=environment)


if __name__ == "__main__":
    main()
