"""Code-generation backends and prompt handling."""

from generation.base import GenerationOutput, GenerationRequest, Generator
from generation.factory import create_generator, register_generator_backend
from generation.gpu_safety import GPUPreflightRefused
from generation.huggingface import HuggingFaceGenerator
from generation.mock import MockGenerator
from generation.ollama import OllamaGenerator

__all__ = [
    "GenerationOutput",
    "GenerationRequest",
    "Generator",
    "HuggingFaceGenerator",
    "GPUPreflightRefused",
    "MockGenerator",
    "OllamaGenerator",
    "create_generator",
    "register_generator_backend",
]
