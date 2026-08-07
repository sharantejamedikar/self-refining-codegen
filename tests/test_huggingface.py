"""Tests for the lazy-loaded Hugging Face Transformers backend."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from generation import GenerationRequest, HuggingFaceGenerator, create_generator
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

    fake_transformers = SimpleNamespace(
        AutoModelForCausalLM=AutoModelForCausalLM,
        AutoTokenizer=AutoTokenizer,
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
