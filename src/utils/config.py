"""Typed experiment configuration loaded from YAML files."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Literal, TypeVar, cast

import yaml


@dataclass(frozen=True)
class ModelConfig:
    """Generation backend and sampling parameters."""

    name: str
    backend: str
    revision: str
    backend_model: str | None = None
    artifact_digest: str | None = None
    quantization: str | None = None
    endpoint: str | None = None
    request_timeout_seconds: float = 300.0
    prompt_strategy: Literal["zero_shot", "few_shot"] = "zero_shot"
    few_shot_examples: int = 2
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
    path: str | None = None


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
    max_iterations: int = 5
    stagnation_patience: int = 2
    oscillation_window: int = 3


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

    model = _construct(ModelConfig, raw["model"])
    if model.prompt_strategy not in {"zero_shot", "few_shot"}:
        raise ValueError("model.prompt_strategy must be 'zero_shot' or 'few_shot'")
    if not 0 <= model.few_shot_examples <= 3:
        raise ValueError("model.few_shot_examples must be between 0 and 3")
    if model.request_timeout_seconds <= 0:
        raise ValueError("model.request_timeout_seconds must be positive")
    if (
        model.backend != "mock"
        and re.fullmatch(r"[0-9a-f]{40}", model.revision) is None
    ):
        raise ValueError(
            "non-mock model.revision must be a full 40-character commit hash"
        )

    experiment = _construct(ExperimentConfig, raw["experiment"])
    if (
        min(
            experiment.max_iterations,
            experiment.stagnation_patience,
            experiment.oscillation_window,
        )
        <= 0
    ):
        raise ValueError("experiment convergence settings must be positive")

    return AppConfig(
        model=model,
        dataset=_construct(DatasetConfig, raw["dataset"]),
        execution=_construct(ExecutionConfig, raw["execution"]),
        experiment=experiment,
        device=_construct(DeviceConfig, device_values),
    )
