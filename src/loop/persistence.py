"""Incremental, atomic persistence for completed problem records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generation.base import GenerationOutput
from utils.config import ModelConfig


def model_provenance(
    model_config: ModelConfig, generation: GenerationOutput
) -> dict[str, Any]:
    """Build explicit per-record model and precision provenance."""

    metadata = dict(generation.backend_metadata or {})
    metadata.setdefault("backend", model_config.backend)
    metadata.setdefault("canonical_model", model_config.name)
    metadata.setdefault("revision", model_config.revision)
    metadata.setdefault("quantization", model_config.quantization)
    metadata.setdefault(
        "result_precision",
        "QUANTIZED" if model_config.quantization is not None else "FULL_PRECISION",
    )
    return metadata


def write_problem_record(problem_directory: Path, record: dict[str, Any]) -> Path:
    """Atomically persist one completed problem record and return its path."""

    filename = str(record["task_id"]).replace("/", "_") + ".json"
    destination = problem_directory / filename
    temporary = problem_directory / f".{filename}.tmp"
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(destination)
    return destination
