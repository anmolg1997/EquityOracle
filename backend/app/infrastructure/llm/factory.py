"""LLM provider factory."""

from __future__ import annotations

from app.config import settings
from app.infrastructure.llm.base import LLMProvider
from app.infrastructure.llm.cost_tracker import LLMCostTracker
from app.infrastructure.llm.gemini import GeminiProvider
from app.infrastructure.llm.ollama import OllamaProvider

_cost_tracker: LLMCostTracker | None = None


def get_cost_tracker() -> LLMCostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = LLMCostTracker(daily_budget_inr=settings.llm.daily_budget_inr)
    return _cost_tracker


def create_llm_provider(prefer_local: bool = False) -> LLMProvider:
    tracker = get_cost_tracker()

    if prefer_local or tracker.should_use_local():
        return OllamaProvider(base_url=settings.llm.ollama_base_url)

    if settings.llm.gemini_api_key:
        return GeminiProvider(api_key=settings.llm.gemini_api_key)

    return OllamaProvider(base_url=settings.llm.ollama_base_url)
