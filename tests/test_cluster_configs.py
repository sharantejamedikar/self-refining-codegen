"""Validation for unquantized Hugging Face cluster preflight configs."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from generation import HuggingFaceGenerator, create_generator
from utils.config import detect_accelerator, load_config


@pytest.mark.parametrize(
    ("filename", "model_name", "revision"),
    [
        (
            "cluster_qwen_hf_zero_shot_humaneval_dev.yaml",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "c03e6d358207e414f1eca0bb1891e29f1db0e242",
        ),
        (
            "cluster_qwen_hf_hybrid_refinement_adaptive_humaneval_dev.yaml",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "c03e6d358207e414f1eca0bb1891e29f1db0e242",
        ),
        (
            "cluster_qwen_hf_best_of_5_humaneval_dev.yaml",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "c03e6d358207e414f1eca0bb1891e29f1db0e242",
        ),
        (
            "cluster_codellama_hf_zero_shot_humaneval_dev.yaml",
            "codellama/CodeLlama-13b-Instruct-hf",
            "745795438019e47e4dad1347a0093e11deee4c68",
        ),
    ],
)
def test_cluster_config_uses_revision_pinned_unquantized_hf_backend(
    filename: str,
    model_name: str,
    revision: str,
) -> None:
    config = load_config(Path("configs") / filename, profile="cluster")

    assert config.model.name == model_name
    assert config.model.backend_model == model_name
    assert config.model.backend == "huggingface"
    assert config.model.revision == revision
    assert config.model.quantization is None
    assert config.device.profile == "cluster"
    assert config.dataset.split == "dev"


def test_cluster_best_of_five_config_uses_diverse_sampling_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_best_of_5_humaneval_dev.yaml"),
        profile="cluster",
    )

    assert config.model.temperature == 0.8
    assert config.experiment.samples_per_problem == 5
    assert config.experiment.seed == 42


def test_cuda_auto_detection_flows_from_cluster_config_to_hf_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: True),
        backends=SimpleNamespace(
            mps=SimpleNamespace(is_available=lambda: True),
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    assert detect_accelerator() == "cuda"
    config = load_config(
        Path("configs/cluster_qwen_hf_zero_shot_humaneval_dev.yaml"),
        profile="cluster",
    )
    generator = create_generator(config.model, config.device.accelerator)

    assert config.device.accelerator == "cuda"
    assert isinstance(generator, HuggingFaceGenerator)
    assert generator.accelerator == "cuda"
