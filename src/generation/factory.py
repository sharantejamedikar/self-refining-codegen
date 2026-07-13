"""Config-driven registry for model generation backends."""

from __future__ import annotations

from collections.abc import Callable

from generation.base import Generator
from generation.ollama import OllamaGenerator
from utils.config import ModelConfig

GeneratorBuilder = Callable[[ModelConfig], Generator]

_BACKENDS: dict[str, GeneratorBuilder] = {"ollama": OllamaGenerator}


def register_generator_backend(name: str, builder: GeneratorBuilder) -> None:
    """Register a backend without changing experiment calling code."""

    normalized = name.strip().lower()
    if not normalized:
        raise ValueError("Backend name cannot be empty")
    _BACKENDS[normalized] = builder


def create_generator(config: ModelConfig) -> Generator:
    """Create the backend selected entirely by typed model configuration."""

    backend = config.backend.strip().lower()
    try:
        builder = _BACKENDS[backend]
    except KeyError as error:
        raise ValueError(
            f"Unsupported generator backend {config.backend!r}; "
            f"registered backends: {sorted(_BACKENDS)}"
        ) from error
    return builder(config)
