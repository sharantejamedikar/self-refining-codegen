"""Tests for typed YAML configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from utils import config as config_module
from utils.config import load_config


def _write_config(path: Path, extra: str = "") -> None:
    path.write_text(
        """
model: {name: mock, backend: mock, revision: fixture-v1}
dataset: {name: humaneval, source_url: 'https://example.invalid/data'}
execution: {backend: subprocess, timeout_seconds: 1, memory_limit_mb: null}
experiment: {name: test, seed: 7, output_dir: runs}
device: {profile: mac, accelerator: auto}
profiles:
  cluster:
    device: {accelerator: cuda}
"""
        + extra,
        encoding="utf-8",
    )


def test_load_config_auto_detection_and_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.yaml"
    _write_config(path)
    monkeypatch.setattr(config_module, "detect_accelerator", lambda: "mps")
    automatic = load_config(path)
    cluster = load_config(path, "cluster")
    assert automatic.device.accelerator == "mps"
    assert cluster.device.accelerator == "cuda"
    assert cluster.device.profile == "cluster"
    assert automatic.experiment.seed == 7


def test_load_config_rejects_invalid_content(tmp_path: Path) -> None:
    invalid_root = tmp_path / "root.yaml"
    invalid_root.write_text("- not-a-mapping\n", encoding="utf-8")
    with pytest.raises(ValueError, match="root"):
        load_config(invalid_root)

    path = tmp_path / "config.yaml"
    _write_config(path, "unexpected: true\n")
    with pytest.raises(ValueError, match="Unknown configuration sections"):
        load_config(path)
    with pytest.raises(ValueError, match="Unknown profile"):
        load_config(path, "colab")


def test_load_config_rejects_missing_and_unknown_fields(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    missing.write_text("model: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing configuration sections"):
        load_config(missing)

    path = tmp_path / "unknown-field.yaml"
    _write_config(path)
    text = path.read_text(encoding="utf-8").replace(
        "revision: fixture-v1", "revision: fixture-v1, mystery: true"
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown ModelConfig fields"):
        load_config(path)


def test_detect_accelerator_without_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def blocked_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked_import)
    assert config_module.detect_accelerator() == "cpu"
