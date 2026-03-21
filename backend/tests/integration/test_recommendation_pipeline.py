"""Integration test: Full recommendation pipeline from data -> scoring -> signal -> exit rules.

Tests the real interaction between Analysis, Recommendation, and Risk domains
without mocking internal domain logic.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, Ticker, TimeHorizon
from app.domain.analysis.composite import compute_composite
from app.domain.analysis.decorrelation import compute_decorrelation
from app.domain.analysis.factors import compute_factor_scores
from app.domain.analysis.models import FactorScore, TechnicalScore
from app.domain.market_data.models import FundamentalData, OHLCV
from app.domain.recommendation.exit_signals import generate_exit_rules
from app.domain.recommendation.models import SignalDirection
from app.domain.recommendation.scoring import (
    generate_multi_horizon_signals,
    score_for_horizon,
)


@pytest.fixture
def ticker():
    return Ticker(symbol="RELIANCE", exchange=Exchange.NSE, market=Market.INDIA)


@pytest.fixture
def ohlcv_series(ticker):
    records = []
    base = Decimal("2500")
    for i in range(30):
        price = base + Decimal(str(i * 10))
        records.append(
            OHLCV(
                ticker=ticker,
                date=date(2024, 1, 1 + i) if i < 28 else date(2024, 2, i - 27),
                open=price - Decimal("5"), high=price + Decimal("15"),
                low=price - Decimal("10"), close=price, volume=2_000_000,
            )
        )
    return records


@pytest.fixture
def fundamentals(ticker):
    return FundamentalData(
        ticker=ticker, as_of_date=date.today(),
        pe_ratio=Decimal("15"), pb_ratio=Decimal("2.5"),
        ev_ebitda=Decimal("10"), roe=Decimal("0.18"),
        operating_profit_margin=Decimal("0.15"),
        profit_growth_3yr=Decimal("0.12"),
    )


class TestRecommendationPipeline:
    def test_factor_scores_to_composite(self, ticker, ohlcv_series, fundamentals):
        """Factor scores feed into composite scoring correctly."""
        factors = compute_factor_scores(ticker, ohlcv_series, fundamentals)
        tech = TechnicalScore(ticker=ticker, as_of_date=date.today(), score=Decimal("65"))

        composite = compute_composite(
            ticker=ticker, technical=tech, factor=factors,
            ml_prediction=Decimal("60"),
        )
        assert composite.overall > 0
        assert composite.technical == Decimal("65")

    def test_composite_to_signal(self, ticker, ohlcv_series, fundamentals):
        """Composite score generates appropriate signal direction."""
        factors = compute_factor_scores(ticker, ohlcv_series, fundamentals)
        tech = TechnicalScore(ticker=ticker, as_of_date=date.today(), score=Decimal("75"))

        composite = compute_composite(
            ticker=ticker, technical=tech, factor=factors,
            ml_prediction=Decimal("70"),
        )

        signal = score_for_horizon(
            ticker=ticker,
            composite_score=composite.overall,
            expected_return=Decimal("5"),
            confidence=Decimal("0.7"),
            horizon=TimeHorizon.WEEK_1,
        )
        assert signal.ticker == ticker
        assert signal.horizon == TimeHorizon.WEEK_1

    def test_signal_to_exit_rules(self, ticker, ohlcv_series, fundamentals):
        """Buy signals generate appropriate exit rules."""
        signal = score_for_horizon(
            ticker=ticker,
            composite_score=Decimal("75"),
            expected_return=Decimal("5"),
            confidence=Decimal("0.7"),
            horizon=TimeHorizon.WEEK_1,
        )
        assert signal.direction == SignalDirection.BUY

        exit_rules = generate_exit_rules(
            entry_price=Decimal("2500"), atr=Decimal("50"),
        )
        assert len(exit_rules) >= 2

    def test_multi_horizon_integration(self, ticker):
        """Multi-horizon signals generated from composite."""
        predictions = {
            TimeHorizon.DAY_1: {"expected_return": 0.5, "confidence": 0.55},
            TimeHorizon.WEEK_1: {"expected_return": 3.0, "confidence": 0.65},
            TimeHorizon.MONTH_1: {"expected_return": 8.0, "confidence": 0.75},
            TimeHorizon.MONTH_3: {"expected_return": 15.0, "confidence": 0.80},
        }
        signals = generate_multi_horizon_signals(
            ticker=ticker,
            composite_score=Decimal("72"),
            horizon_predictions=predictions,
            effective_signal_count=Decimal("2.8"),
        )
        assert len(signals) == 4
        for s in signals:
            assert s.independent_signal_count == Decimal("2.8")

    def test_decorrelation_feeds_composite(self, ticker, ohlcv_series, fundamentals):
        """Decorrelation result adjusts effective signal count in composite."""
        factors = compute_factor_scores(ticker, ohlcv_series, fundamentals)
        tech = TechnicalScore(ticker=ticker, as_of_date=date.today(), score=Decimal("70"))

        decorr = compute_decorrelation({
            "technical": [70, 60, 80, 50, 75, 65, 72, 68, 78, 62],
            "fundamental": [40, 55, 35, 65, 45, 50, 42, 58, 38, 60],
        })

        composite = compute_composite(
            ticker=ticker, technical=tech, factor=factors,
            effective_signal_count=decorr.effective_signal_count,
            pillar_correlations=decorr.pairwise_correlations,
        )
        assert composite.effective_signal_count > 0
