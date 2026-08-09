"""Sustained GPU-idleness checks for shared multi-GPU model loading."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


class GPUPreflightRefused(RuntimeError):
    """Raised when a shared GPU cannot be proven idle."""


@dataclass(frozen=True)
class GPUReading:
    """One timestamped utilization and memory observation."""

    timestamp_utc: str
    utilization_percent: float
    memory_used_mb: float


@dataclass(frozen=True)
class GPUPreflightResult:
    """Auditable outcome of a sustained shared-GPU safety check."""

    gpu_index: int
    idle: bool
    utilization_threshold_percent: float
    memory_threshold_mb: float
    sample_interval_seconds: float
    readings: tuple[GPUReading, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe provenance representation."""

        return asdict(self)


def query_gpu_reading(gpu_index: int) -> GPUReading:
    """Read one GPU's state using the installed ``nvidia-smi`` command."""

    command = [
        "nvidia-smi",
        f"--id={gpu_index}",
        "--query-gpu=utilization.gpu,memory.used",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        fields = [part.strip() for part in completed.stdout.strip().split(",")]
        if len(fields) != 2:
            raise ValueError(f"unexpected output: {completed.stdout!r}")
        utilization, memory_used = (float(value) for value in fields)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError) as error:
        raise GPUPreflightRefused(
            f"GPU {gpu_index} safety check failed; refusing multi-GPU operation: "
            f"{error}"
        ) from error
    return GPUReading(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        utilization_percent=utilization,
        memory_used_mb=memory_used,
    )


def check_gpu_idle(
    gpu_index: int,
    *,
    sample_count: int = 3,
    sample_interval_seconds: float = 3.0,
    utilization_threshold_percent: float = 5.0,
    memory_threshold_mb: float = 500.0,
    query: Callable[[int], GPUReading] = query_gpu_reading,
    sleep: Callable[[float], None] = time.sleep,
) -> GPUPreflightResult:
    """Require every sustained sample to be strictly below both thresholds."""

    if sample_count < 2:
        raise ValueError("GPU preflight requires at least two samples")
    if sample_interval_seconds <= 0:
        raise ValueError("GPU preflight sample interval must be positive")
    if utilization_threshold_percent <= 0 or memory_threshold_mb <= 0:
        raise ValueError("GPU preflight thresholds must be positive")

    readings: list[GPUReading] = []
    for sample_index in range(sample_count):
        readings.append(query(gpu_index))
        if sample_index + 1 < sample_count:
            sleep(sample_interval_seconds)
    idle = all(
        reading.utilization_percent < utilization_threshold_percent
        and reading.memory_used_mb < memory_threshold_mb
        for reading in readings
    )
    return GPUPreflightResult(
        gpu_index=gpu_index,
        idle=idle,
        utilization_threshold_percent=utilization_threshold_percent,
        memory_threshold_mb=memory_threshold_mb,
        sample_interval_seconds=sample_interval_seconds,
        readings=tuple(readings),
    )


def require_gpu_idle(**kwargs: Any) -> GPUPreflightResult:
    """Run the sustained check and refuse access unless every sample is idle."""

    result = check_gpu_idle(**kwargs)
    if not result.idle:
        raise GPUPreflightRefused(
            f"GPU {result.gpu_index} is not sustainably idle; refusing multi-GPU "
            "operation. No model will be loaded. "
            f"Readings: {result.to_dict()['readings']}"
        )
    return result
