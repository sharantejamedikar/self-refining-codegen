"""Build validated, normalized benchmark datasets and seeded development splits."""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from data import (
    HUMANEVAL_PRO_URL,
    HUMANEVAL_URL,
    MBPP_PRO_URL,
    MBPP_SANITIZED_URL,
    AtomicSplitReport,
    Problem,
    create_stratified_dev_split,
    download_file,
    load_codeeval_pro,
    load_humaneval_with_report,
    load_mbpp_sanitized,
    validate_problems,
    write_atomic_split_report,
    write_jsonl,
)
from execution import SubprocessExecutor

HUMANEVAL_COUNT = 164
MBPP_SANITIZED_COUNT = 427
HUMANEVAL_DEV_COUNT = 20
MBPP_DEV_COUNT = 50
HUMANEVAL_PRO_COUNT = 164
MBPP_PRO_COUNT = 378
HUMANEVAL_ABLATION_COUNT = 100
DEFAULT_SEED = 42


def parse_args() -> argparse.Namespace:
    """Parse dataset build settings."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--memory-limit-mb", type=int, default=512)
    return parser.parse_args()


def _require_count(name: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise RuntimeError(f"{name}: expected {expected} records, found {actual}")


def _load_historical_humaneval(
    path: Path,
) -> tuple[list[Problem], list[dict[str, Any]]]:
    """Reproduce the compound-harness layout used by the frozen M7 runs."""

    with gzip.open(path, mode="rt", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    required = {"task_id", "prompt", "canonical_solution", "test", "entry_point"}
    problems: list[Problem] = []
    for record in records:
        missing = required - set(record)
        if missing:
            raise ValueError(f"HumanEval record is missing {sorted(missing)}")
        problems.append(
            Problem(
                task_id=str(record["task_id"]),
                prompt=str(record["prompt"]),
                canonical_solution=(
                    f"{record['prompt']}{record['canonical_solution']}"
                ),
                test_cases=(f"{record['test']}\ncheck({record['entry_point']})",),
                difficulty="unspecified",
                tags=("humaneval",),
            )
        )
    return problems, records


def _load_atomic_humaneval_dev(
    records: list[dict[str, Any]], selected_ids: set[str]
) -> tuple[list[Problem], AtomicSplitReport]:
    """Atomically normalize the already selected historical development tasks."""

    selected = [record for record in records if str(record["task_id"]) in selected_ids]
    if len(selected) != HUMANEVAL_DEV_COUNT:
        raise RuntimeError(
            "HumanEval-Dev raw selection mismatch: "
            f"expected {HUMANEVAL_DEV_COUNT}, found {len(selected)}"
        )
    with tempfile.NamedTemporaryFile(suffix=".jsonl.gz") as source:
        with gzip.open(source.name, mode="wt", encoding="utf-8") as handle:
            for record in selected:
                handle.write(json.dumps(record) + "\n")
        return load_humaneval_with_report(source.name)


def main() -> None:
    """Download, normalize, validate, and split both primary benchmarks."""

    args = parse_args()
    data_dir: Path = args.data_dir
    raw_dir = data_dir / "raw"
    normalized_dir = data_dir / "normalized"
    dev_dir = data_dir / "dev"
    validation_dir = data_dir / "validation"
    # Superseded name from an aborted strict-full build; the historical full set
    # is intentionally compound, while only HumanEval-Dev has an atomic report.
    (validation_dir / "humaneval_atomic_split_report.json").unlink(missing_ok=True)

    humaneval_source = download_file(
        HUMANEVAL_URL,
        raw_dir / "HumanEval.jsonl.gz",
    )
    mbpp_source = download_file(
        MBPP_SANITIZED_URL,
        raw_dir / "sanitized-mbpp.json",
    )
    humaneval_pro_source = download_file(
        HUMANEVAL_PRO_URL, raw_dir / "humaneval_pro.json"
    )
    mbpp_pro_source = download_file(MBPP_PRO_URL, raw_dir / "mbpp_pro.json")

    humaneval, humaneval_records = _load_historical_humaneval(humaneval_source)
    mbpp = load_mbpp_sanitized(mbpp_source)
    humaneval_pro = load_codeeval_pro(humaneval_pro_source, "humaneval_pro")
    mbpp_pro = load_codeeval_pro(mbpp_pro_source, "mbpp_pro")
    _require_count("HumanEval", len(humaneval), HUMANEVAL_COUNT)
    _require_count("sanitized MBPP", len(mbpp), MBPP_SANITIZED_COUNT)
    _require_count("HumanEval Pro", len(humaneval_pro), HUMANEVAL_PRO_COUNT)
    _require_count("MBPP Pro", len(mbpp_pro), MBPP_PRO_COUNT)

    executor = SubprocessExecutor(
        timeout_seconds=args.timeout_seconds,
        memory_limit_mb=args.memory_limit_mb,
    )
    humaneval_validation = validate_problems(
        humaneval, executor, validation_dir / "humaneval_quarantine.jsonl"
    )
    mbpp_validation = validate_problems(
        mbpp, executor, validation_dir / "mbpp_sanitized_quarantine.jsonl"
    )
    humaneval_pro_validation = validate_problems(
        humaneval_pro, executor, validation_dir / "humaneval_pro_quarantine.jsonl"
    )
    mbpp_pro_validation = validate_problems(
        mbpp_pro, executor, validation_dir / "mbpp_pro_quarantine.jsonl"
    )
    if (
        humaneval_validation.quarantined
        or mbpp_validation.quarantined
        or humaneval_pro_validation.quarantined
        or mbpp_pro_validation.quarantined
    ):
        raise RuntimeError(
            "Canonical validation failed: "
            f"HumanEval={len(humaneval_validation.quarantined)}, "
            f"MBPP={len(mbpp_validation.quarantined)} quarantined; "
            f"HumanEval Pro={len(humaneval_pro_validation.quarantined)}, "
            f"MBPP Pro={len(mbpp_pro_validation.quarantined)} quarantined; "
            f"see {validation_dir}"
        )

    selected_humaneval = create_stratified_dev_split(
        humaneval_validation.valid,
        HUMANEVAL_DEV_COUNT,
        args.seed,
        dev_dir / "humaneval_dev.jsonl",
    )
    humaneval_dev, dev_atomic_report = _load_atomic_humaneval_dev(
        humaneval_records, {problem.task_id for problem in selected_humaneval}
    )
    write_atomic_split_report(
        dev_atomic_report,
        validation_dir / "humaneval_dev_atomic_split_report.json",
    )
    if dev_atomic_report.failed:
        raise RuntimeError(
            "HumanEval-Dev atomic splitting failed; see "
            f"{validation_dir / 'humaneval_dev_atomic_split_report.json'}"
        )
    humaneval_dev_validation = validate_problems(
        humaneval_dev,
        executor,
        validation_dir / "humaneval_dev_quarantine.jsonl",
    )
    if humaneval_dev_validation.quarantined:
        raise RuntimeError(
            "HumanEval-Dev canonical validation failed: "
            f"{len(humaneval_dev_validation.quarantined)} quarantined"
        )

    humaneval_normalized = write_jsonl(
        humaneval_validation.valid, normalized_dir / "humaneval.jsonl"
    )
    mbpp_normalized = write_jsonl(
        mbpp_validation.valid, normalized_dir / "mbpp_sanitized.jsonl"
    )
    humaneval_pro_normalized = write_jsonl(
        humaneval_pro_validation.valid, normalized_dir / "humaneval_pro.jsonl"
    )
    mbpp_pro_normalized = write_jsonl(
        mbpp_pro_validation.valid, normalized_dir / "mbpp_pro.jsonl"
    )
    humaneval_dev = list(humaneval_dev_validation.valid)
    write_jsonl(
        humaneval_dev,
        dev_dir / "humaneval_dev.jsonl",
    )
    mbpp_dev = create_stratified_dev_split(
        mbpp_validation.valid,
        MBPP_DEV_COUNT,
        args.seed,
        dev_dir / "mbpp_dev.jsonl",
    )
    humaneval_ablation = create_stratified_dev_split(
        humaneval_validation.valid,
        HUMANEVAL_ABLATION_COUNT,
        args.seed,
        dev_dir / "humaneval_ablation_100.jsonl",
    )

    print(
        f"HumanEval: {len(humaneval_validation.valid)} validated -> "
        f"{humaneval_normalized}"
    )
    print(
        f"MBPP sanitized: {len(mbpp_validation.valid)} validated -> "
        f"{mbpp_normalized}"
    )
    print(f"HumanEval-Dev: {len(humaneval_dev)} (seed {args.seed})")
    print(f"MBPP-Dev: {len(mbpp_dev)} (seed {args.seed})")
    print(
        f"HumanEval Pro: {len(humaneval_pro_validation.valid)} validated -> "
        f"{humaneval_pro_normalized}"
    )
    print(
        f"MBPP Pro: {len(mbpp_pro_validation.valid)} validated -> {mbpp_pro_normalized}"
    )
    print(f"HumanEval ablation: {len(humaneval_ablation)} (seed {args.seed})")
    print(f"Validation reports: {validation_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
