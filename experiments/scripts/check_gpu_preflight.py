"""Run only the shared-GPU safety check; never load a model."""

from __future__ import annotations

import argparse
import json

from generation.gpu_safety import GPUPreflightRefused, check_gpu_idle


def main() -> None:
    """Print timestamped readings and exit successfully for either outcome."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--interval-seconds", type=float, default=3.0)
    parser.add_argument("--utilization-threshold-percent", type=float, default=25.0)
    parser.add_argument("--memory-threshold-mb", type=float, default=500.0)
    args = parser.parse_args()
    result = check_gpu_idle(
        args.gpu_index,
        sample_count=args.samples,
        sample_interval_seconds=args.interval_seconds,
        utilization_threshold_percent=args.utilization_threshold_percent,
        memory_threshold_mb=args.memory_threshold_mb,
    )
    print(json.dumps(result.to_dict(), indent=2))
    print(f"GPU {args.gpu_index}: {'IDLE' if result.idle else 'BUSY — REFUSE ACCESS'}")


if __name__ == "__main__":
    try:
        main()
    except GPUPreflightRefused as error:
        raise SystemExit(f"SAFETY REFUSAL: {error}") from None
