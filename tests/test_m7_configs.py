"""Validation for quantized local-development M7 full-set configurations."""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.config import load_config

CONFIGURATIONS = [
    "m7_qwen_ollama_q4_local_single_humaneval_full.yaml",
    "m7_qwen_ollama_q4_local_single_mbpp_full.yaml",
    "m7_qwen_ollama_q4_local_best_of_5_humaneval_full.yaml",
    "m7_qwen_ollama_q4_local_best_of_5_mbpp_full.yaml",
    "m7_qwen_ollama_q4_local_hybrid_refinement_adaptive_humaneval_full.yaml",
    "m7_qwen_ollama_q4_local_hybrid_refinement_adaptive_mbpp_full.yaml",
    "m7_qwen_ollama_q4_local_hybrid_refinement_fixed_humaneval_full.yaml",
    "m7_qwen_ollama_q4_local_hybrid_refinement_fixed_mbpp_full.yaml",
]


@pytest.mark.parametrize("filename", CONFIGURATIONS)
def test_m7_full_config_is_explicitly_quantized_local_development(
    filename: str,
) -> None:
    config = load_config(Path("configs") / filename, profile="mac")

    assert config.dataset.split == "full"
    assert config.dataset.path in {
        "data/normalized/humaneval.jsonl",
        "data/normalized/mbpp_sanitized.jsonl",
    }
    assert config.model.backend == "ollama"
    assert config.model.quantization == "Q4_K_M"
    assert "quantized_local_development" in config.experiment.name
    assert config.device.profile == "mac"


@pytest.mark.parametrize(
    "filename",
    [name for name in CONFIGURATIONS if "refinement" in name],
)
def test_m7_refinement_configs_select_hybrid_and_stopping_mode(
    filename: str,
) -> None:
    config = load_config(Path("configs") / filename, profile="mac")

    expected_mode = "fixed" if "_fixed_" in filename else "adaptive"
    assert config.experiment.feedback_strategy == "hybrid"
    assert config.experiment.convergence_mode == expected_mode
    assert config.experiment.max_iterations == 5
    assert config.execution.collect_trace
