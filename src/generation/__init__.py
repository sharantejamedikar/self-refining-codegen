"""Code-generation backends and prompt handling."""

from generation.base import GenerationOutput, Generator
from generation.mock import MockGenerator

__all__ = ["GenerationOutput", "Generator", "MockGenerator"]
