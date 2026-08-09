"""Tests for the lazy-loaded Hugging Face Transformers backend."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from generation import GenerationRequest, HuggingFaceGenerator, create_generator
from generation.gpu_safety import GPUPreflightResult, GPUReading
from utils.config import ModelConfig


def _config(**overrides: Any) -> ModelConfig:
    values: dict[str, Any] = {
        "name": "org/generic-code-model",
        "backend": "huggingface",
        "revision": "a" * 40,
        "backend_model": "org/generic-code-model",
    }
    values.update(overrides)
    return ModelConfig(**values)


class _Tensor:
    def __init__(self, values: list[int]) -> None:
        self.values = values
        self.shape = (1, len(values))
        self.device: str | None = None

    def to(self, device: str) -> _Tensor:
        self.device = device
        return self

    def __getitem__(self, item: object) -> _Tensor:
        if isinstance(item, tuple):
            return _Tensor(self.values[item[1]])
        if item == 0:
            return self
        raise TypeError(item)


class _Tokenizer:
    eos_token_id = 2
    pad_token_id = None

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
        return_tensors: str,
    ) -> _Tensor:
        assert tokenize and add_generation_prompt and return_tensors == "pt"
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        return _Tensor([10, 11, 12])

    def decode(self, token_ids: _Tensor, *, skip_special_tokens: bool) -> str:
        assert skip_special_tokens
        assert token_ids.values == [20, 21]
        return "```python\ndef answer():\n    return 42\n```"


class _Model:
    device = SimpleNamespace(type="cuda")

    def __init__(self) -> None:
        self.generation_kwargs: dict[str, Any] = {}

    def eval(self) -> _Model:
        return self

    def generate(self, inputs: _Tensor, **kwargs: Any) -> _Tensor:
        assert inputs.device == "cuda"
        self.generation_kwargs = kwargs
        return _Tensor([10, 11, 12, 20, 21])

    def get_memory_footprint(self) -> int:
        return 13_000_000_000


def test_huggingface_generation_is_config_and_device_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tokenizer = _Tokenizer()
    model = _Model()
    captured: dict[str, Any] = {}

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(name: str, **kwargs: Any) -> _Tokenizer:
            captured["tokenizer"] = (name, kwargs)
            return tokenizer

    class AutoModelForCausalLM:
        @staticmethod
        def from_pretrained(name: str, **kwargs: Any) -> _Model:
            captured["model"] = (name, kwargs)
            return model

    class BitsAndBytesConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    fake_transformers = SimpleNamespace(
        AutoModelForCausalLM=AutoModelForCausalLM,
        AutoTokenizer=AutoTokenizer,
        BitsAndBytesConfig=BitsAndBytesConfig,
    )
    fake_torch = SimpleNamespace(
        manual_seed=lambda seed: captured.setdefault("seed", seed),
        ones_like=lambda tensor: captured.setdefault("attention_mask", tensor),
        bfloat16="bfloat16",
        float16="float16",
        float32="float32",
    )
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    generator = HuggingFaceGenerator(
        _config(temperature=0.25, max_new_tokens=99), accelerator="cuda"
    )
    output = generator.generate(GenerationRequest("def answer():\n    pass", 73))

    assert output.code == "def answer():\n    return 42"
    assert output.prompt_tokens == 3
    assert output.completion_tokens == 2
    assert (
        output.backend_metadata and output.backend_metadata["backend"] == "huggingface"
    )
    assert output.backend_metadata["accelerator"] == "cuda"
    assert output.backend_metadata["result_precision"] == "FULL_PRECISION"
    assert output.backend_metadata["model_memory_footprint_bytes"] == 13_000_000_000
    assert captured["tokenizer"] == (
        "org/generic-code-model",
        {"revision": "a" * 40},
    )
    assert captured["model"][1]["revision"] == "a" * 40
    assert captured["model"][1]["device_map"] == "cuda"
    assert model.generation_kwargs["max_new_tokens"] == 99
    assert model.generation_kwargs["temperature"] == 0.25
    assert model.generation_kwargs["do_sample"] is True
    assert captured["seed"] == 73
    assert "generator" not in model.generation_kwargs
    assert model.generation_kwargs["attention_mask"] is captured["attention_mask"]
    assert "attention_mask" not in output.request_payload["generation_options"]
    assert output.request_payload and output.request_payload["seed"] == 73


def test_huggingface_backend_is_lazy_and_factory_receives_accelerator() -> None:
    generator = create_generator(_config(), accelerator="cuda")
    assert isinstance(generator, HuggingFaceGenerator)
    assert generator.accelerator == "cuda"


def test_huggingface_rejects_missing_model_and_unsupported_accelerator() -> None:
    with pytest.raises(ValueError, match="backend_model"):
        HuggingFaceGenerator(_config(backend_model=None), accelerator="cpu")
    with pytest.raises(ValueError, match="accelerator"):
        HuggingFaceGenerator(_config(), accelerator="tpu")
    with pytest.raises(ValueError, match="requires the CUDA"):
        HuggingFaceGenerator(
            _config(quantization="bitsandbytes_8bit"), accelerator="cpu"
        )
    with pytest.raises(ValueError, match="quantization must be"):
        HuggingFaceGenerator(_config(quantization="GPTQ"), accelerator="cuda")


@pytest.mark.parametrize(
    ("quantization", "expected_options"),
    [
        ("bitsandbytes_8bit", {"load_in_8bit": True}),
        (
            "bitsandbytes_4bit",
            {
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": "bfloat16",
                "bnb_4bit_quant_type": "nf4",
                "bnb_4bit_use_double_quant": True,
            },
        ),
    ],
)
def test_huggingface_builds_bitsandbytes_config_and_records_provenance(
    monkeypatch: pytest.MonkeyPatch,
    quantization: str,
    expected_options: dict[str, Any],
) -> None:
    tokenizer = _Tokenizer()
    model = _Model()
    captured: dict[str, Any] = {}

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(name: str, **kwargs: Any) -> _Tokenizer:
            return tokenizer

    class AutoModelForCausalLM:
        @staticmethod
        def from_pretrained(name: str, **kwargs: Any) -> _Model:
            captured.update(kwargs)
            return model

    class BitsAndBytesConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoModelForCausalLM=AutoModelForCausalLM,
            AutoTokenizer=AutoTokenizer,
            BitsAndBytesConfig=BitsAndBytesConfig,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            manual_seed=lambda seed: None,
            ones_like=lambda tensor: tensor,
            bfloat16="bfloat16",
            float16="float16",
            float32="float32",
        ),
    )

    output = HuggingFaceGenerator(
        _config(quantization=quantization), accelerator="cuda"
    ).generate(GenerationRequest("def answer():\n    pass", 42))

    assert captured["quantization_config"].kwargs == expected_options
    assert output.backend_metadata is not None
    assert output.backend_metadata["result_precision"] == "QUANTIZED"
    assert output.backend_metadata["quantization_method"] == "bitsandbytes"
    assert output.backend_metadata["quantization_config"] == expected_options


def test_device_map_auto_is_gated_and_preflight_is_retained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    result = GPUPreflightResult(
        gpu_index=1,
        idle=True,
        utilization_threshold_percent=5.0,
        memory_threshold_mb=500.0,
        sample_interval_seconds=3.0,
        readings=(GPUReading("2026-08-09T12:00:00+00:00", 0.0, 100.0),) * 3,
    )

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(name: str, **kwargs: Any) -> _Tokenizer:
            return _Tokenizer()

    class AutoModelForCausalLM:
        @staticmethod
        def from_pretrained(name: str, **kwargs: Any) -> _Model:
            captured["load_options"] = kwargs
            return _Model()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoModelForCausalLM=AutoModelForCausalLM,
            AutoTokenizer=AutoTokenizer,
            BitsAndBytesConfig=object,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(bfloat16="bfloat16", float16="float16", float32="float32"),
    )
    def preflight(**kwargs: Any) -> GPUPreflightResult:
        captured["preflight_kwargs"] = kwargs
        return result

    monkeypatch.setattr("generation.huggingface.require_gpu_idle", preflight)

    generator = HuggingFaceGenerator(
        _config(device_map="auto", gpu_preflight_index=1), accelerator="cuda"
    )
    generator._load()

    assert captured["preflight_kwargs"]["gpu_index"] == 1
    assert captured["load_options"]["device_map"] == "auto"
    assert generator._gpu_preflight == result


def test_device_map_auto_requires_explicit_safety_gate() -> None:
    with pytest.raises(ValueError, match="gpu_preflight_index"):
        HuggingFaceGenerator(_config(device_map="auto"), accelerator="cuda")
