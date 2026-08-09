"""Tests for sustained shared-GPU preflight checks."""

from __future__ import annotations

import subprocess

import pytest

from generation.gpu_safety import (
    GPUPreflightRefused,
    GPUReading,
    check_gpu_idle,
    query_gpu_reading,
    require_gpu_idle,
)


def _reading(utilization: float, memory: float) -> GPUReading:
    return GPUReading("2026-08-09T12:00:00+00:00", utilization, memory)


def test_sustained_idle_requires_every_sample_below_both_thresholds() -> None:
    readings = iter([_reading(0, 100), _reading(4.9, 499), _reading(0, 200)])
    sleeps: list[float] = []

    result = check_gpu_idle(
        1, query=lambda index: next(readings), sleep=sleeps.append
    )

    assert result.idle is True
    assert len(result.readings) == 3
    assert sleeps == [3.0, 3.0]
    assert result.to_dict()["gpu_index"] == 1


@pytest.mark.parametrize("busy", [_reading(5, 100), _reading(0, 500)])
def test_threshold_is_strict_and_one_busy_sample_refuses(busy: GPUReading) -> None:
    readings = iter([_reading(0, 100), busy, _reading(0, 100)])

    with pytest.raises(GPUPreflightRefused, match="refusing multi-GPU"):
        require_gpu_idle(
            gpu_index=1,
            query=lambda index: next(readings),
            sleep=lambda seconds: None,
        )


def test_query_failure_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, "nvidia-smi")

    monkeypatch.setattr(subprocess, "run", fail)

    with pytest.raises(GPUPreflightRefused, match="refusing multi-GPU"):
        query_gpu_reading(1)
