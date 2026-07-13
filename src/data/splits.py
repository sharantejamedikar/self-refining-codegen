"""Reproducible stratified development-set construction."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from data.loaders import write_jsonl
from data.schema import Problem


def create_stratified_dev_split(
    problems: Iterable[Problem],
    size: int,
    seed: int,
    output_path: str | Path,
) -> list[Problem]:
    """Select a seeded proportional sample, with an ordering-quartile fallback.

    Official HumanEval and sanitized MBPP do not provide difficulty labels. When
    the normalized difficulty/tags yield only one stratum, task-ID rank quartiles
    ensure coverage across the benchmark ordering without inventing difficulty.
    """

    pool = sorted(problems, key=_task_sort_key)
    if not 0 < size <= len(pool):
        raise ValueError("size must be positive and no larger than the dataset")

    semantic = {(problem.difficulty, problem.tags) for problem in pool}
    use_quartiles = len(semantic) == 1
    strata: dict[str, list[Problem]] = defaultdict(list)
    for index, problem in enumerate(pool):
        if use_quartiles:
            key = f"task_id_quartile_{min(3, index * 4 // len(pool)) + 1}"
        else:
            key = f"{problem.difficulty}|{'|'.join(problem.tags)}"
        strata[key].append(problem)

    allocations = _proportional_allocations(strata, size, len(pool))
    rng = random.Random(seed)
    selected: list[Problem] = []
    selected_counts: dict[str, int] = {}
    for key in sorted(strata):
        count = allocations[key]
        selected.extend(rng.sample(strata[key], count))
        selected_counts[key] = count
    selected.sort(key=_task_sort_key)

    destination = write_jsonl(selected, output_path)
    metadata = {
        "seed": seed,
        "size": size,
        "source_size": len(pool),
        "stratification": "task_id_rank_quartile" if use_quartiles else "difficulty_tags",
        "strata_selected": selected_counts,
        "task_ids": [problem.task_id for problem in selected],
    }
    metadata_path = destination.with_suffix(destination.suffix + ".meta.json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return selected


def _proportional_allocations(
    strata: dict[str, list[Problem]], size: int, total: int
) -> dict[str, int]:
    exact = {key: size * len(items) / total for key, items in strata.items()}
    allocation = {key: int(value) for key, value in exact.items()}
    remaining = size - sum(allocation.values())
    order = sorted(strata, key=lambda key: (-(exact[key] - allocation[key]), key))
    for key in order[:remaining]:
        allocation[key] += 1
    return allocation


def _task_sort_key(problem: Problem) -> tuple[str, int, int | str]:
    prefix, separator, suffix = problem.task_id.rpartition("/")
    if separator and suffix.isdigit():
        return prefix, 0, int(suffix)
    return problem.task_id, 1, problem.task_id
