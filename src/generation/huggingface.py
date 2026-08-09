"""Hugging Face Transformers generation backend with optional quantization."""

from __future__ import annotations

from typing import Any

from generation.base import GenerationOutput, GenerationRequest, Generator
from generation.extraction import extract_python
from generation.gpu_safety import GPUPreflightResult, require_gpu_idle
from generation.prompts import build_prompt
from utils.config import ModelConfig


class HuggingFaceGenerator(Generator):
    """Generate code with a revision-pinned Transformers causal language model."""

    def __init__(self, config: ModelConfig, accelerator: str) -> None:
        if not config.backend_model:
            raise ValueError("Hugging Face backend requires model.backend_model")
        if accelerator not in {"cuda", "mps", "cpu"}:
            raise ValueError("Hugging Face accelerator must be 'cuda', 'mps', or 'cpu'")
        if config.quantization is not None and accelerator != "cuda":
            raise ValueError("bitsandbytes quantization requires the CUDA accelerator")
        if config.quantization not in {
            None,
            "bitsandbytes_8bit",
            "bitsandbytes_4bit",
        }:
            raise ValueError(
                "Hugging Face quantization must be 'bitsandbytes_8bit', "
                "'bitsandbytes_4bit', or null"
            )
        if config.device_map not in {None, "auto"}:
            raise ValueError("Hugging Face model.device_map must be 'auto' or null")
        if config.device_map == "auto" and accelerator != "cuda":
            raise ValueError("device_map='auto' multi-GPU loading requires CUDA")
        if config.device_map == "auto" and config.gpu_preflight_index is None:
            raise ValueError("device_map='auto' requires model.gpu_preflight_index")
        self.config = config
        self.accelerator = accelerator
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._gpu_preflight: GPUPreflightResult | None = None

    def generate(self, request: GenerationRequest) -> GenerationOutput:
        """Generate one candidate and return backend-neutral output metadata."""

        torch, tokenizer, model = self._load()
        rendered = build_prompt(
            request.problem_prompt,
            strategy=self.config.prompt_strategy,
            few_shot_examples=self.config.few_shot_examples,
            previous_code=request.previous_code,
            feedback=request.feedback,
        )
        messages = [
            {"role": "system", "content": rendered.system},
            {"role": "user", "content": rendered.user},
        ]
        input_ids = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self.accelerator)
        torch.manual_seed(request.seed)
        generation_options = {
            "max_new_tokens": self.config.max_new_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "repetition_penalty": self.config.repetition_penalty,
            "do_sample": self.config.temperature > 0,
            "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
            "attention_mask": torch.ones_like(input_ids),
        }
        generated_ids = model.generate(input_ids, **generation_options)
        completion_ids = generated_ids[:, input_ids.shape[-1] :]
        raw_text = tokenizer.decode(completion_ids[0], skip_special_tokens=True)
        extraction = extract_python(raw_text, request.problem_prompt)
        prompt_tokens = int(input_ids.shape[-1])
        completion_tokens = int(completion_ids.shape[-1])
        finish_reason = (
            "length" if completion_tokens >= self.config.max_new_tokens else "stop"
        )
        request_payload = {
            "model": self.config.backend_model,
            "revision": self.config.revision,
            "messages": messages,
            "seed": request.seed,
            "generation_options": {
                key: value
                for key, value in generation_options.items()
                if key != "attention_mask"
            },
            "quantization": self._quantization_metadata(torch),
        }
        return GenerationOutput(
            code=extraction.code,
            raw_text=raw_text,
            rendered_system_prompt=rendered.system,
            rendered_user_prompt=rendered.user,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
            extraction_method=extraction.method,
            syntax_valid=extraction.syntax_valid,
            request_payload=request_payload,
            backend_metadata={
                "backend": "huggingface",
                "canonical_model": self.config.name,
                "revision": self.config.revision,
                "model": self.config.backend_model,
                "accelerator": self.accelerator,
                "device_map": self.config.device_map or self.accelerator,
                "gpu_preflight": (
                    self._gpu_preflight.to_dict() if self._gpu_preflight else None
                ),
                "dtype": str(self._dtype(torch)),
                "quantization": self.config.quantization,
                **self._quantization_metadata(torch),
                "model_memory_footprint_bytes": int(model.get_memory_footprint()),
                "prompt_strategy": self.config.prompt_strategy,
            },
        )

    def _load(self) -> tuple[Any, Any, Any]:
        if self._tokenizer is not None and self._model is not None:
            import torch

            return torch, self._tokenizer, self._model
        try:
            import torch
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )
        except ImportError as error:
            raise RuntimeError(
                "Hugging Face backend requires the cluster dependencies; "
                "install the project with the 'cluster' extra"
            ) from error

        if self.config.device_map == "auto":
            self._gpu_preflight = require_gpu_idle(
                gpu_index=self.config.gpu_preflight_index,
                sample_count=self.config.gpu_preflight_samples,
                sample_interval_seconds=self.config.gpu_preflight_interval_seconds,
                utilization_threshold_percent=(
                    self.config.gpu_idle_utilization_threshold_percent
                ),
                memory_threshold_mb=self.config.gpu_idle_memory_threshold_mb,
            )

        load_options = {
            "revision": self.config.revision,
            "torch_dtype": self._dtype(torch),
            "device_map": self.config.device_map or self.accelerator,
        }
        quantization_options = self._quantization_options(torch)
        if quantization_options is not None:
            load_options["quantization_config"] = BitsAndBytesConfig(
                **quantization_options
            )
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.backend_model,
            revision=self.config.revision,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.backend_model,
            **load_options,
        )
        self._model.eval()
        return torch, self._tokenizer, self._model

    def get_memory_footprint(self) -> int:
        """Return the loaded model's parameter and buffer footprint in bytes."""

        _, _, model = self._load()
        return int(model.get_memory_footprint())

    def _dtype(self, torch: Any) -> Any:
        if self.accelerator == "cuda":
            return torch.bfloat16
        if self.accelerator == "mps":
            return torch.float16
        return torch.float32

    def _quantization_options(self, torch: Any) -> dict[str, Any] | None:
        """Return validated bitsandbytes constructor options for this model."""

        if self.config.quantization is None:
            return None
        if self.config.quantization == "bitsandbytes_8bit":
            return {"load_in_8bit": True}
        if self.config.quantization == "bitsandbytes_4bit":
            return {
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": self._dtype(torch),
                "bnb_4bit_quant_type": "nf4",
                "bnb_4bit_use_double_quant": True,
            }
        raise AssertionError("quantization was validated during initialization")

    def _quantization_metadata(self, torch: Any) -> dict[str, Any]:
        """Return JSON-safe precision provenance for persisted results."""

        options = self._quantization_options(torch)
        if options is None:
            return {
                "result_precision": "FULL_PRECISION",
                "quantization_method": None,
                "quantization_config": None,
            }
        serialized = {
            key: str(value) if key == "bnb_4bit_compute_dtype" else value
            for key, value in options.items()
        }
        return {
            "result_precision": "QUANTIZED",
            "quantization_method": "bitsandbytes",
            "quantization_config": serialized,
        }
