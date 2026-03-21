"""Risk domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.core.types import CircuitBreakerState


@dataclass
class RiskCheckResult:
    approved: bool
    reasons: list[str] = field(default_factory=list)
    adjusted_quantity: int | None = None


@dataclass
class DrawdownState:
    peak_value: Decimal = Decimal(0)
    current_value: Decimal = Decimal(0)

    @property
    def drawdown_pct(self) -> Decimal:
        if self.peak_value == 0:
            return Decimal(0)
        return ((self.peak_value - self.current_value) / self.peak_value) * 100

    def update(self, value: Decimal) -> None:
        self.current_value = value
        if value > self.peak_value:
            self.peak_value = value


@dataclass
class CircuitBreakerLog:
    previous_state: CircuitBreakerState
    new_state: CircuitBreakerState
    trigger_reason: str
    metrics: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
