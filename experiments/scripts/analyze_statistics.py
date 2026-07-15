"""Compute a reproducible offline statistical report from committed results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis import analyze_plan, load_analysis_plan


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--repository-root", default=".")
    return parser.parse_args()


def main() -> None:
    """Load the plan, analyze persisted JSON, and write the configured report."""

    args = parse_args()
    plan = load_analysis_plan(args.config)
    root = Path(args.repository_root)
    report = analyze_plan(plan, root)
    output = root / plan.output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
