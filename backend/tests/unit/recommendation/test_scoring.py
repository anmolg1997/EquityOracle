"""Tests for multi-horizon scoring and signal generation."""

from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, Ticker, TimeHorizon
from app.domain.recommendation.models import SignalDirection
from app.domain.recommendation.scoring import (
    generate_multi_horizon_signals,
    score_for_horizon,
)


@pytest.fixture
def ticker():
    return Ticker(symbol="TCS", exchange=Exchange.NSE, market=Market.INDIA)


class TestScoreForHorizon:
    def test_buy_signal_on_high_composite(self, ticker):
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("75"),
            expected_return=Decimal("5"),
            confidence=Decimal("0.7"),
            horizon=TimeHorizon.WEEK_1,
        )
        assert signal.direction == SignalDirection.BUY
        assert signal.strength == Decimal("75")

    def test_sell_signal_on_low_composite(self, ticker):
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("30"),
            expected_return=Decimal("-5"),
            confidence=Decimal("0.6"),
            horizon=TimeHorizon.WEEK_1,
        )
        assert signal.direction == SignalDirection.SELL

    def test_hold_signal_on_medium_composite(self, ticker):
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("50"),
            expected_return=Decimal("2"),
            confidence=Decimal("0.5"),
            horizon=TimeHorizon.WEEK_1,
        )
        assert signal.direction == SignalDirection.HOLD

    def test_sell_on_negative_return_despite_high_composite(self, ticker):
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("55"),
            expected_return=Decimal("-4"),
            confidence=Decimal("0.5"),
            horizon=TimeHorizon.DAY_1,
        )
        assert signal.direction == SignalDirection.SELL

    def test_signal_carries_horizon(self, ticker):
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("70"),
            expected_return=Decimal("3"),
            confidence=Decimal("0.8"),
            horizon=TimeHorizon.MONTH_3,
        )
        assert signal.horizon == TimeHorizon.MONTH_3

    def test_signal_carries_effective_signal_count(self, ticker):
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("70"),
            expected_return=Decimal("3"),
            confidence=Decimal("0.8"),
            horizon=TimeHorizon.DAY_3,
            effective_signal_count=Decimal("2.5"),
        )
        assert signal.independent_signal_count == Decimal("2.5")


class TestMultiHorizonSignals:
    def test_generates_signals_for_all_horizons(self, ticker):
        predictions = {
            TimeHorizon.DAY_1: {"expected_return": 1.0, "confidence": 0.6},
            TimeHorizon.WEEK_1: {"expected_return": 3.0, "confidence": 0.7},
            TimeHorizon.MONTH_1: {"expected_return": 8.0, "confidence": 0.8},
        }
        signals = generate_multi_horizon_signals(
            ticker=ticker,
            composite_score=Decimal("70"),
            horizon_predictions=predictions,
        )
        assert len(signals) == 3
        horizons = {s.horizon for s in signals}
        assert TimeHorizon.DAY_1 in horizons
        assert TimeHorizon.WEEK_1 in horizons
        assert TimeHorizon.MONTH_1 in horizons

    def test_empty_predictions_returns_empty(self, ticker):
        signals = generate_multi_horizon_signals(
            ticker=ticker,
            composite_score=Decimal("70"),
            horizon_predictions={},
        )
        assert len(signals) == 0
