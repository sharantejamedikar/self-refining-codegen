"""Incremental, atomic persistence for completed problem records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
