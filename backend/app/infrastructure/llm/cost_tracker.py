"""LLM cost tracker — token counting, daily budget cap, selective debate gating."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.core.logging import get_logger

log = get_logger(__name__)

# Approximate pricing per 1K tokens (INR)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini/gemini-2.0-flash": {"input": 0.005, "output": 0.015},
    "gemini/gemini-1.5-pro": {"input": 0.025, "output": 0.075},
    "ollama/llama3.2": {"input": 0.0, "output": 0.0},
}


@dataclass
class CostEntry:
    model: str
    input_tokens: int
    output_tokens: int
    cost_inr: float
    purpose: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LLMCostTracker:
    """Tracks LLM usage costs and enforces daily budget caps."""

    def __init__(self, daily_budget_inr: float = 50.0) -> None:
        self._budget = daily_budget_inr
        self._entries: list[CostEntry] = []
        self._today: date = date.today()

    @property
    def today_spend(self) -> float:
        self._maybe_reset()
        return sum(e.cost_inr for e in self._entries if e.timestamp.date() == self._today)

    @property
    def budget_remaining(self) -> float:
        return max(0, self._budget - self.today_spend)

    def can_afford(self, estimated_cost: float = 0.1) -> bool:
        return self.budget_remaining >= estimated_cost

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        purpose: str = "general",
    ) -> CostEntry:
        pricing = MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

        entry = CostEntry(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_inr=round(cost, 4),
            purpose=purpose,
        )
        self._entries.append(entry)

        log.info(
            "llm_cost_recorded",
            model=model,
            tokens=input_tokens + output_tokens,
            cost_inr=entry.cost_inr,
            budget_remaining=self.budget_remaining,
        )

        return entry

    def should_use_local(self) -> bool:
        """When budget is low, recommend switching to local (free) Ollama."""
        return self.budget_remaining < self._budget * 0.2

    def get_daily_summary(self) -> dict:
        self._maybe_reset()
        today_entries = [e for e in self._entries if e.timestamp.date() == self._today]
        return {
            "date": str(self._today),
            "total_spend_inr": round(self.today_spend, 4),
            "budget_inr": self._budget,
            "remaining_inr": round(self.budget_remaining, 4),
            "calls": len(today_entries),
            "total_tokens": sum(e.input_tokens + e.output_tokens for e in today_entries),
            "recommend_local": self.should_use_local(),
        }

    def _maybe_reset(self) -> None:
        today = date.today()
        if today != self._today:
            self._today = today
