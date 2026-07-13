"""Generic Ollama generation backend using the local HTTP API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from generation.base import GenerationOutput, GenerationRequest, Generator
from generation.extraction import extract_python
from generation.prompts import build_prompt
from utils.config import ModelConfig


class OllamaGenerator(Generator):
    """Generate code with any Ollama model described by :class:`ModelConfig`."""

    def __init__(self, config: ModelConfig) -> None:
        if not config.backend_model:
            raise ValueError("Ollama backend requires model.backend_model")
        if not config.endpoint:
            raise ValueError("Ollama backend requires model.endpoint")
        if not config.artifact_digest:
            raise ValueError("Ollama backend requires model.artifact_digest")
        self.config = config

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        """Call Ollama once and extract an executable Python candidate."""

        rendered = build_prompt(
            request.problem_prompt,
            strategy=self.config.prompt_strategy,
            few_shot_examples=self.config.few_shot_examples,
        )
        payload = {
            "model": self.config.backend_model,
            "system": rendered.system,
            "prompt": rendered.user,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "num_predict": self.config.max_new_tokens,
                "repeat_penalty": self.config.repetition_penalty,
                "seed": request.seed,
            },
        }
        response = self._post_json("/api/generate", payload)
        raw_text = response.get("response")
        if not isinstance(raw_text, str):
            raise RuntimeError("Ollama response is missing string field 'response'")
        extraction = extract_python(raw_text, request.problem_prompt)
        return GenerationOutput(
            code=extraction.code,
            raw_text=raw_text,
            prompt_tokens=_optional_int(response.get("prompt_eval_count")),
            completion_tokens=_optional_int(response.get("eval_count")),
            finish_reason=_optional_string(response.get("done_reason")),
            extraction_method=extraction.method,
            syntax_valid=extraction.syntax_valid,
            backend_metadata={
                "backend": "ollama",
                "canonical_model": self.config.name,
                "revision": self.config.revision,
                "model": response.get("model", self.config.backend_model),
                "artifact_digest": self.config.artifact_digest,
                "quantization": self.config.quantization,
                "prompt_strategy": self.config.prompt_strategy,
                "created_at": response.get("created_at"),
                "total_duration_ns": response.get("total_duration"),
                "load_duration_ns": response.get("load_duration"),
                "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
                "eval_duration_ns": response.get("eval_duration"),
            },
        )

    def verify_artifact(self) -> dict[str, Any]:
        """Verify the configured model tag and optional immutable Ollama digest."""

        response = self._get_json("/api/tags")
        models = response.get("models")
        if not isinstance(models, list):
            raise RuntimeError("Ollama tags response is missing list field 'models'")
        for model in models:
            if not isinstance(model, dict):
                continue
            names = {model.get("name"), model.get("model")}
            if self.config.backend_model in names:
                digest = model.get("digest")
                if (
                    self.config.artifact_digest
                    and digest != self.config.artifact_digest
                ):
                    raise RuntimeError(
                        "Ollama artifact digest mismatch: "
                        f"expected {self.config.artifact_digest}, got {digest}"
                    )
                details = model.get("details")
                actual_quantization = (
                    details.get("quantization_level")
                    if isinstance(details, dict)
                    else None
                )
                if (
                    self.config.quantization
                    and actual_quantization != self.config.quantization
                ):
                    raise RuntimeError(
                        "Ollama quantization mismatch: "
                        f"expected {self.config.quantization}, "
                        f"got {actual_quantization}"
                    )
                return model
        raise RuntimeError(
            f"Ollama model is not installed: {self.config.backend_model}"
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self._url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._open_json(request)

    def _get_json(self, path: str) -> dict[str, Any]:
        return self._open_json(urllib.request.Request(self._url(path), method="GET"))

    def _open_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(  # noqa: S310 - endpoint is explicit config.
                request, timeout=self.config.request_timeout_seconds
            ) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.config.endpoint}"
            ) from error
        except json.JSONDecodeError as error:
            raise RuntimeError("Ollama returned invalid JSON") from error
        if not isinstance(decoded, dict):
            raise RuntimeError("Ollama response root must be an object")
        return decoded

    def _url(self, path: str) -> str:
        return f"{self.config.endpoint.rstrip('/')}{path}"


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None
