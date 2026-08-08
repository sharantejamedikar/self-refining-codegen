"""Regression tests for environment defaults installed by run entry points."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "script_name",
    [
        "run_best_of_k.py",
        "run_mock_single_pass.py",
        "run_refinement.py",
        "run_single_pass.py",
    ],
)
def test_run_script_disables_tokenizer_parallelism_by_default(
    monkeypatch: pytest.MonkeyPatch, script_name: str
) -> None:
    monkeypatch.delenv("TOKENIZERS_PARALLELISM", raising=False)

    runpy.run_path(Path("experiments/scripts") / script_name)

    assert __import__("os").environ["TOKENIZERS_PARALLELISM"] == "false"


def test_run_script_preserves_explicit_tokenizer_parallelism_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOKENIZERS_PARALLELISM", "true")

    runpy.run_path(Path("experiments/scripts/run_best_of_k.py"))

    assert __import__("os").environ["TOKENIZERS_PARALLELISM"] == "true"
