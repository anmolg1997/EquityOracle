"""Pure domain models for the Recommendation bounded context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from app.core.types import Ticker, TimeHorizon


class SignalDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class ExitType(str, Enum):
    TRAILING_STOP = "trailing_stop"
    ATR_EXIT = "atr_exit"
    TECHNICAL_REVERSAL = "technical_reversal"
    THESIS_INVALIDATION = "thesis_invalidation"
    TIME_EXPIRY = "time_expiry"


@dataclass
class Signal:
    ticker: Ticker
    direction: SignalDirection
    horizon: TimeHorizon
    strength: Decimal  # 0-100
    expected_return_pct: Decimal
    confidence: Decimal  # 0-1 calibrated probability
    independent_signal_count: Decimal = Decimal(0)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExitRule:
    exit_type: ExitType
    trigger_value: Decimal  # e.g., stop price, ATR multiplier
    description: str = ""

    def is_triggered(self, current_price: Decimal, entry_price: Decimal, atr: Decimal | None = None) -> bool:
        match self.exit_type:
            case ExitType.TRAILING_STOP:
                return current_price <= self.trigger_value
            case ExitType.ATR_EXIT:
                if atr and entry_price > 0:
                    stop = entry_price - (atr * self.trigger_value)
                    return current_price <= stop
            case ExitType.TIME_EXPIRY:
                return False  # handled by date check
        return False


@dataclass
class Thesis:
    ticker: Ticker
    summary: str
    entry_triggers: list[str] = field(default_factory=list)
    monitoring_conditions: list[str] = field(default_factory=list)
    invalidation_triggers: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    cached_until: datetime | None = None


@dataclass
class DebateResult:
    ticker: Ticker
    bull_case: str = ""
    bear_case: str = ""
    synthesis: str = ""
    verdict: SignalDirection = SignalDirection.HOLD
    scenario_probabilities: dict[str, float] = field(default_factory=dict)
    evidence_quality: str = "medium"


@dataclass
class DecisionAudit:
    """Full decision context for a single recommendation — immutable record."""

    correlation_id: str
    ticker: Ticker
    horizon: TimeHorizon
    decision: SignalDirection
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Raw inputs
    technical_score: Decimal = Decimal(0)
    factor_score: Decimal = Decimal(0)
    sentiment_score: Decimal = Decimal(0)
    ml_prediction: Decimal = Decimal(0)

    # Weights and decorrelation
    weights_used: dict[str, float] = field(default_factory=dict)
    pillar_correlations: dict[str, float] = field(default_factory=dict)
    effective_signal_count: Decimal = Decimal(0)

    # Composite
    composite_score: Decimal = Decimal(0)
    confidence: Decimal = Decimal(0)

    # Risk checks
    risk_check_passed: bool = True
    risk_check_reasons: list[str] = field(default_factory=list)

    # Data quality
    data_quality_flags: list[str] = field(default_factory=list)

    # Context
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    signal: Signal
    exit_rules: list[ExitRule] = field(default_factory=list)
    thesis: Thesis | None = None
    debate: DebateResult | None = None
    audit: DecisionAudit | None = None

    # Tracking
    actual_return_pct: Decimal | None = None
    outcome_date: date | None = None
    is_accurate: bool | None = None
