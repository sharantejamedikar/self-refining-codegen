"""Full-precision Hugging Face Transformers generation backend."""

from __future__ import annotations

from typing import Any

from generation.base import GenerationOutput, GenerationRequest, Generator
from generation.extraction import extract_python
from generation.prompts import build_prompt
from utils.config import ModelConfig


class HuggingFaceGenerator(Generator):
    """Generate code with a revision-pinned Transformers causal language model."""

    def __init__(self, config: ModelConfig, accelerator: str) -> None:
        if not config.backend_model:
            raise ValueError("Hugging Face backend requires model.backend_model")
        if accelerator not in {"cuda", "mps", "cpu"}:
            raise ValueError("Hugging Face accelerator must be 'cuda', 'mps', or 'cpu'")
        self.config = config
        self.accelerator = accelerator
        self._tokenizer: Any | None = None
        self._model: Any | None = None

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
        generator = torch.Generator(device=self.accelerator)
        generator.manual_seed(request.seed)
        generation_options = {
            "max_new_tokens": self.config.max_new_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "repetition_penalty": self.config.repetition_penalty,
            "do_sample": self.config.temperature > 0,
            "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
            "generator": generator,
        }
        generated_ids = model.generate(input_ids, **generation_options)
        completion_ids = generated_ids[:, input_ids.shape[-1] :]
        raw_text = tokenizer.decode(completion_ids, skip_special_tokens=True)
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
                if key != "generator"
            },
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
                "dtype": str(self._dtype(torch)),
                "quantization": self.config.quantization,
                "prompt_strategy": self.config.prompt_strategy,
            },
        )

    def _load(self) -> tuple[Any, Any, Any]:
        if self._tokenizer is not None and self._model is not None:
            import torch

            return torch, self._tokenizer, self._model
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "Hugging Face backend requires the cluster dependencies; "
                "install the project with the 'cluster' extra"
            ) from error

        load_options = {
            "revision": self.config.revision,
            "torch_dtype": self._dtype(torch),
            "device_map": self.accelerator,
        }
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

    def _dtype(self, torch: Any) -> Any:
        if self.accelerator == "cuda":
            return torch.bfloat16
        if self.accelerator == "mps":
            return torch.float16
        return torch.float32
