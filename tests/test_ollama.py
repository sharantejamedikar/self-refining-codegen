"""Tests for the generic Ollama backend and backend registry."""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from generation import GenerationRequest, OllamaGenerator, create_generator
from generation.factory import register_generator_backend
from generation.mock import MockGenerator
from utils.config import ModelConfig


def _config(**overrides: Any) -> ModelConfig:
    values: dict[str, Any] = {
        "name": "org/generic-code-model",
        "backend": "ollama",
        "revision": "a" * 40,
        "backend_model": "generic-code:7b-q4",
        "artifact_digest": "sha256:fixture",
        "quantization": "Q4_K_M",
        "endpoint": "http://127.0.0.1:11434",
    }
    values.update(overrides)
    return ModelConfig(**values)


class _Response:
    def __init__(self, payload: dict[str, Any] | bytes) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


def test_ollama_generation_is_config_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_open(request: Any, timeout: float) -> _Response:
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response(
            {
                "model": "generic-code:7b-q4",
                "response": "```python\ndef answer():\n    return 42\n```",
                "done_reason": "stop",
                "prompt_eval_count": 21,
                "eval_count": 9,
                "total_duration": 100,
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    generator = OllamaGenerator(_config(temperature=0.25, max_new_tokens=99))
    output = generator.generate(GenerationRequest("def answer():\n    pass", 73))
    assert output.code == "def answer():\n    return 42"
    assert output.raw_text.startswith("```python")
    assert output.prompt_tokens == 21 and output.completion_tokens == 9
    assert output.backend_metadata and output.backend_metadata["backend"] == "ollama"
    assert captured["url"].endswith("/api/generate")
    assert captured["payload"]["model"] == "generic-code:7b-q4"
    assert captured["payload"]["options"] == {
        "temperature": 0.25,
        "top_p": 0.95,
        "num_predict": 99,
        "repeat_penalty": 1.1,
        "seed": 73,
    }


def test_ollama_verifies_tag_and_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: _Response(
            {
                "models": [
                    {
                        "name": "generic-code:7b-q4",
                        "digest": "sha256:fixture",
                        "details": {"quantization_level": "Q4_K_M"},
                    }
                ]
            }
        ),
    )
    assert OllamaGenerator(_config()).verify_artifact()["digest"] == "sha256:fixture"
    with pytest.raises(RuntimeError, match="digest mismatch"):
        OllamaGenerator(_config(artifact_digest="sha256:other")).verify_artifact()
    with pytest.raises(RuntimeError, match="quantization mismatch"):
        OllamaGenerator(_config(quantization="Q8_0")).verify_artifact()


def test_ollama_reports_configuration_and_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="backend_model"):
        OllamaGenerator(_config(backend_model=None))
    with pytest.raises(ValueError, match="endpoint"):
        OllamaGenerator(_config(endpoint=None))
    with pytest.raises(ValueError, match="artifact_digest"):
        OllamaGenerator(_config(artifact_digest=None))

    def unavailable(*args: object, **kwargs: object) -> _Response:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    with pytest.raises(RuntimeError, match="Cannot connect"):
        OllamaGenerator(_config()).generate(GenerationRequest("def x(): pass", 1))


def test_backend_factory_is_extensible_without_calling_code_changes() -> None:
    backend = "test_backend_fixture"

    def build(config: ModelConfig) -> MockGenerator:
        del config
        return MockGenerator({}, default_output="x = 1")

    register_generator_backend(backend, build)
    created = create_generator(_config(backend=backend))
    assert isinstance(created, MockGenerator)
    with pytest.raises(ValueError, match="Unsupported generator backend"):
        create_generator(_config(backend="not_registered"))
