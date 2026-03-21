"""Multi-horizon scoring and confidence calibration."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.core.types import Ticker, TimeHorizon
from app.domain.recommendation.models import Signal, SignalDirection


def score_for_horizon(
    ticker: Ticker,
    composite_score: Decimal,
    expected_return: Decimal,
    confidence: Decimal,
    horizon: TimeHorizon,
    effective_signal_count: Decimal = Decimal(0),
) -> Signal:
    """Generate a signal for a specific horizon based on composite score."""
    direction = SignalDirection.HOLD
    if composite_score >= Decimal(65) and expected_return > Decimal(0):
        direction = SignalDirection.BUY
    elif composite_score <= Decimal(35) or expected_return < Decimal("-3"):
        direction = SignalDirection.SELL

    return Signal(
        ticker=ticker,
        direction=direction,
        horizon=horizon,
        strength=composite_score,
        expected_return_pct=expected_return,
        confidence=confidence,
        independent_signal_count=effective_signal_count,
        generated_at=datetime.utcnow(),
    )


def generate_multi_horizon_signals(
    ticker: Ticker,
    composite_score: Decimal,
    horizon_predictions: dict[TimeHorizon, dict],
    effective_signal_count: Decimal = Decimal(0),
) -> list[Signal]:
    """Generate signals across all requested horizons."""
    signals: list[Signal] = []

    for horizon, pred in horizon_predictions.items():
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=composite_score,
            expected_return=Decimal(str(pred.get("expected_return", 0))),
            confidence=Decimal(str(pred.get("confidence", 0.5))),
            horizon=horizon,
            effective_signal_count=effective_signal_count,
        )
        signals.append(signal)

    return signals
