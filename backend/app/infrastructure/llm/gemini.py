"""Google Gemini adapter via litellm."""

from __future__ import annotations

from typing import AsyncIterator

from litellm import acompletion

from app.core.logging import get_logger
from app.infrastructure.llm.base import LLMProvider

log = get_logger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini/gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await acompletion(
                model=self._model,
                messages=messages,
                api_key=self._api_key,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            log.error("gemini_generation_failed", error=str(e))
            raise

    async def stream(self, prompt: str, system: str = "") -> AsyncIterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await acompletion(
                model=self._model,
                messages=messages,
                api_key=self._api_key,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            log.error("gemini_stream_failed", error=str(e))
            raise
