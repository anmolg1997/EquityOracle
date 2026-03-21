"""LLM provider port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMProvider(ABC):
    """Port: LLM for thesis, debate, and news analysis."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        ...

    @abstractmethod
    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
