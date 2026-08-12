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
        (
            "cluster_codellama_hf_zero_shot_mbpp_dev.yaml",
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
    if model_name.startswith("codellama/"):
        assert config.model.device_map == "auto"
        assert config.model.gpu_preflight_index == 1
        assert config.model.gpu_preflight_samples == 3
        assert config.model.gpu_preflight_interval_seconds == 3.0
    assert config.device.profile == "cluster"
    assert config.dataset.split == "dev"


@pytest.mark.parametrize(
    ("filename", "dataset_name", "dataset_path"),
    [
        (
            "cluster_codellama_hf_zero_shot_humaneval_dev.yaml",
            "humaneval",
            "data/dev/humaneval_dev.jsonl",
        ),
        (
            "cluster_codellama_hf_zero_shot_mbpp_dev.yaml",
            "mbpp",
            "data/dev/mbpp_dev.jsonl",
        ),
    ],
)
def test_codellama_preflight_configs_use_frozen_dev_protocol(
    filename: str,
    dataset_name: str,
    dataset_path: str,
) -> None:
    config = load_config(Path("configs") / filename, profile="cluster")

    assert config.model.temperature == 0.2
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == dataset_name
    assert config.dataset.path == dataset_path
    assert config.experiment.seed == 42


def test_cluster_best_of_five_config_uses_diverse_sampling_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_best_of_5_humaneval_dev.yaml"),
        profile="cluster",
    )

    assert config.model.temperature == 0.8
    assert config.experiment.samples_per_problem == 5
    assert config.experiment.seed == 42


def test_cluster_full_best_of_five_config_uses_frozen_tier_one_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_best_of_5_humaneval_full.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "c03e6d358207e414f1eca0bb1891e29f1db0e242"
    assert config.model.quantization is None
    assert config.model.temperature == 0.8
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/humaneval.jsonl"
    assert config.experiment.samples_per_problem == 5
    assert config.experiment.seed == 42


def test_codellama_8bit_full_best_of_five_uses_frozen_protocol() -> None:
    config = load_config(
        Path("configs/cluster_codellama_hf_bnb_8bit_best_of_5_humaneval_full.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "745795438019e47e4dad1347a0093e11deee4c68"
    assert config.model.quantization == "bitsandbytes_8bit"
    assert config.model.temperature == 0.8
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == "humaneval"
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/humaneval.jsonl"
    assert config.experiment.samples_per_problem == 5
    assert config.experiment.seed == 42
    assert config.device.accelerator == "cuda"


def test_cluster_full_mbpp_single_config_uses_guarded_tier_one_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_zero_shot_mbpp_full.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "c03e6d358207e414f1eca0bb1891e29f1db0e242"
    assert config.model.quantization is None
    assert config.model.temperature == 0.2
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == "mbpp"
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/mbpp_sanitized.jsonl"
    assert config.experiment.seed == 42


def test_cluster_full_mbpp_best_of_five_uses_frozen_tier_one_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_best_of_5_mbpp_full.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "c03e6d358207e414f1eca0bb1891e29f1db0e242"
    assert config.model.quantization is None
    assert config.model.temperature == 0.8
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == "mbpp"
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/mbpp_sanitized.jsonl"
    assert config.experiment.samples_per_problem == 5
    assert config.experiment.seed == 42


def test_cluster_full_mbpp_adaptive_refinement_uses_frozen_tier_one_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_hybrid_refinement_adaptive_mbpp_full.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "c03e6d358207e414f1eca0bb1891e29f1db0e242"
    assert config.model.quantization is None
    assert config.model.temperature == 0.2
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == "mbpp"
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/mbpp_sanitized.jsonl"
    assert config.execution.collect_trace is True
    assert config.experiment.max_iterations == 5
    assert config.experiment.stagnation_patience == 2
    assert config.experiment.oscillation_window == 3
    assert config.experiment.feedback_strategy == "hybrid"
    assert config.experiment.convergence_mode == "adaptive"
    assert config.experiment.seed == 42


def test_cluster_full_mbpp_fixed_refinement_uses_frozen_tier_one_protocol() -> None:
    config = load_config(
        Path("configs/cluster_qwen_hf_hybrid_refinement_fixed_mbpp_full.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "c03e6d358207e414f1eca0bb1891e29f1db0e242"
    assert config.model.quantization is None
    assert config.model.temperature == 0.2
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == "mbpp"
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/mbpp_sanitized.jsonl"
    assert config.execution.collect_trace is True
    assert config.experiment.max_iterations == 5
    assert config.experiment.stagnation_patience == 2
    assert config.experiment.oscillation_window == 3
    assert config.experiment.feedback_strategy == "hybrid"
    assert config.experiment.convergence_mode == "fixed"
    assert config.experiment.seed == 42


def test_codellama_8bit_full_mbpp_adaptive_refinement_uses_frozen_protocol() -> None:
    config = load_config(
        Path(
            "configs/cluster_codellama_hf_bnb_8bit_hybrid_refinement_adaptive_mbpp_full.yaml"
        ),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "745795438019e47e4dad1347a0093e11deee4c68"
    assert config.model.quantization == "bitsandbytes_8bit"
    assert config.model.temperature == 0.2
    assert config.model.top_p == 0.95
    assert config.model.max_new_tokens == 512
    assert config.model.repetition_penalty == 1.1
    assert config.dataset.name == "mbpp"
    assert config.dataset.split == "full"
    assert config.dataset.path == "data/normalized/mbpp_sanitized.jsonl"
    assert config.execution.collect_trace is True
    assert config.experiment.max_iterations == 5
    assert config.experiment.stagnation_patience == 2
    assert config.experiment.oscillation_window == 3
    assert config.experiment.feedback_strategy == "hybrid"
    assert config.experiment.convergence_mode == "adaptive"
    assert config.experiment.seed == 42
    assert config.device.accelerator == "cuda"


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


def test_codellama_bitsandbytes_smoke_config_is_explicitly_quantized() -> None:
    config = load_config(
        Path("configs/cluster_codellama_hf_bnb_8bit_zero_shot_humaneval_dev.yaml"),
        profile="cluster",
    )

    assert config.model.backend == "huggingface"
    assert config.model.revision == "745795438019e47e4dad1347a0093e11deee4c68"
    assert config.model.quantization == "bitsandbytes_8bit"
    assert config.dataset.name == "humaneval"
    assert config.dataset.split == "dev"
    assert config.dataset.path == "data/dev/humaneval_dev.jsonl"
    assert config.device.accelerator == "cuda"
    assert "quantized_development" in config.experiment.name
