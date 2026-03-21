"""Tests for weighted composite scoring logic."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, Ticker
from app.domain.analysis.composite import compute_composite
from app.domain.analysis.models import FactorScore, SentimentScore, TechnicalScore


@pytest.fixture
def ticker():
    return Ticker(symbol="INFY", exchange=Exchange.NSE, market=Market.INDIA)


@pytest.fixture
def tech_score(ticker):
    return TechnicalScore(ticker=ticker, as_of_date=date.today(), score=Decimal("70"))


@pytest.fixture
def factor_score(ticker):
    return FactorScore(
        ticker=ticker, as_of_date=date.today(),
        momentum_score=Decimal("60"), quality_score=Decimal("70"),
        value_score=Decimal("80"), composite=Decimal("70"),
    )


@pytest.fixture
def sentiment_score(ticker):
    return SentimentScore(
        ticker=ticker, as_of_date=date.today(), composite=Decimal("0.6"),
    )


class TestCompositeScoring:
    def test_default_weights(self, ticker, tech_score, factor_score, sentiment_score):
        result = compute_composite(
            ticker=ticker,
            technical=tech_score,
            factor=factor_score,
            sentiment=sentiment_score,
            ml_prediction=Decimal("65"),
        )
        assert result.overall > 0
        assert result.weights_used["technical"] == 0.25

    def test_custom_weights(self, ticker, tech_score, factor_score):
        custom_w = {"technical": 0.5, "fundamental": 0.5, "sentiment": 0.0, "ml_prediction": 0.0}
        result = compute_composite(
            ticker=ticker,
            technical=tech_score,
            factor=factor_score,
            weights=custom_w,
        )
        expected = Decimal(str(round(float(tech_score.score) * 0.5 + float(factor_score.composite) * 0.5, 2)))
        assert abs(result.overall - expected) < Decimal("1")

    def test_no_sentiment_uses_default_50(self, ticker, tech_score, factor_score):
        result = compute_composite(
            ticker=ticker,
            technical=tech_score,
            factor=factor_score,
            sentiment=None,
        )
        assert result.sentiment == Decimal(0)
        assert result.overall > 0

    def test_confidence_level_high(self, ticker):
        tech = TechnicalScore(ticker=ticker, as_of_date=date.today(), score=Decimal("95"))
        factor = FactorScore(ticker=ticker, as_of_date=date.today(), composite=Decimal("90"))
        result = compute_composite(
            ticker=ticker, technical=tech, factor=factor,
            ml_prediction=Decimal("90"),
        )
        assert result.confidence_level in ("high", "medium")

    def test_confidence_level_low(self, ticker):
        tech = TechnicalScore(ticker=ticker, as_of_date=date.today(), score=Decimal("20"))
        factor = FactorScore(ticker=ticker, as_of_date=date.today(), composite=Decimal("20"))
        result = compute_composite(
            ticker=ticker, technical=tech, factor=factor,
            ml_prediction=Decimal("20"),
        )
        assert result.confidence_level == "low"
