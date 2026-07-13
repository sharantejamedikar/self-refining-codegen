"""Regenerate tracked atomic-split validation evidence for HumanEval-Dev."""

from __future__ import annotations

import argparse
import gzip
import json
import tempfile
from pathlib import Path
from typing import Any

from data import load_humaneval_with_report, write_atomic_split_report


def parse_args() -> argparse.Namespace:
    """Parse validation artifact paths."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="data/raw/HumanEval.jsonl.gz")
    parser.add_argument(
        "--dev-metadata", default="data/dev/humaneval_dev.jsonl.meta.json"
    )
    parser.add_argument(
        "--output",
        default="docs/validation/humaneval_dev_atomic_split_report.json",
    )
    return parser.parse_args()


def _selected_records(
    source: str | Path, dev_metadata: str | Path
) -> list[dict[str, Any]]:
    metadata = json.loads(Path(dev_metadata).read_text(encoding="utf-8"))
    requested_ids = [str(task_id) for task_id in metadata["task_ids"]]
    requested = set(requested_ids)
    with gzip.open(source, mode="rt", encoding="utf-8") as handle:
        records = [
            record
            for line in handle
            if (record := json.loads(line)).get("task_id") in requested
        ]
    found = {str(record["task_id"]) for record in records}
    missing = requested - found
    if missing or len(records) != len(requested_ids):
        raise ValueError(
            "HumanEval-Dev source selection mismatch: "
            f"expected {len(requested_ids)}, found {len(records)}, "
            f"missing {sorted(missing)}"
        )
    return records


def main() -> None:
    """Split the seeded dev harnesses and persist their validation report."""

    args = parse_args()
    records = _selected_records(args.source, args.dev_metadata)
    with tempfile.NamedTemporaryFile(suffix=".jsonl.gz") as selected_source:
        with gzip.open(selected_source.name, mode="wt", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        _, report = load_humaneval_with_report(selected_source.name)

    destination = write_atomic_split_report(report, args.output)
    print(
        f"{destination}: {report.atomically_split}/{report.total_harnesses} safe, "
        f"{report.total_assertions} atomic assertions, {report.failed} unsafe"
    )
    if report.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
