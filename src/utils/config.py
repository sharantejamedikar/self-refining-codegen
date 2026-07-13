"""Typed experiment configuration loaded from YAML files."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, TypeVar, cast

import yaml


@dataclass(frozen=True)
class ModelConfig:
    """Generation backend and sampling parameters."""

    name: str
    backend: str
    revision: str
    temperature: float = 0.2
    top_p: float = 0.95
    max_new_tokens: int = 512
    repetition_penalty: float = 1.1


@dataclass(frozen=True)
class DatasetConfig:
    """Dataset source and local storage settings."""

    name: str
    source_url: str
    data_dir: str = "data"
    split: str = "dev"


@dataclass(frozen=True)
class ExecutionConfig:
    """Limits applied by the execution backend."""

    backend: str = "subprocess"
    timeout_seconds: float = 10.0
    memory_limit_mb: int | None = 512
    python_executable: str = "python3"


@dataclass(frozen=True)
class ExperimentConfig:
    """Run-level controls and output settings."""

    name: str = "m1_mock_single_pass"
    seed: int = 42
    output_dir: str = "experiments/results"


@dataclass(frozen=True)
class DeviceConfig:
    """Resolved execution environment and accelerator choice."""

    profile: str = "mac"
    accelerator: str = "auto"


@dataclass(frozen=True)
class AppConfig:
    """Complete typed configuration for one experiment run."""

    model: ModelConfig
    dataset: DatasetConfig
    execution: ExecutionConfig
    experiment: ExperimentConfig
    device: DeviceConfig


T = TypeVar("T")


def detect_accelerator() -> str:
    """Return the best available accelerator in CUDA, MPS, CPU priority order."""

    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _construct(cls: type[T], values: dict[str, Any]) -> T:
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")
    allowed = {field.name for field in fields(cls)}
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} fields: {sorted(unknown)}")
    return cls(**values)


def load_config(path: str | Path, profile: str | None = None) -> AppConfig:
    """Load YAML into :class:`AppConfig`, optionally applying a named profile."""

    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a mapping")

    profiles = raw.pop("profiles", {})
    if profile is not None:
        if profile not in profiles:
            raise ValueError(
                f"Unknown profile {profile!r}; choose from {sorted(profiles)}"
            )
        raw = _deep_merge(raw, cast(dict[str, Any], profiles[profile]))
        raw.setdefault("device", {})["profile"] = profile

    required = {"model", "dataset", "execution", "experiment", "device"}
    missing = required - set(raw)
    if missing:
        raise ValueError(f"Missing configuration sections: {sorted(missing)}")
    unknown = set(raw) - required
    if unknown:
        raise ValueError(f"Unknown configuration sections: {sorted(unknown)}")

    device_values = dict(raw["device"])
    if device_values.get("accelerator", "auto") == "auto":
        device_values["accelerator"] = detect_accelerator()

    return AppConfig(
        model=_construct(ModelConfig, raw["model"]),
        dataset=_construct(DatasetConfig, raw["dataset"]),
        execution=_construct(ExecutionConfig, raw["execution"]),
        experiment=_construct(ExperimentConfig, raw["experiment"]),
        device=_construct(DeviceConfig, device_values),
    )
