"""Tests for factor scoring — Momentum, Quality, Value."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, Ticker
from app.domain.analysis.factors import compute_factor_scores
from app.domain.market_data.models import FundamentalData, OHLCV


@pytest.fixture
def ticker():
    return Ticker(symbol="RELIANCE", exchange=Exchange.NSE, market=Market.INDIA)


def _make_series(ticker, n_days, base_price, growth_pct=0.0):
    """Generate n_days of OHLCV with optional linear growth."""
    records = []
    for i in range(n_days):
        price = base_price + Decimal(str(i * float(base_price) * growth_pct / 100))
        d = date(2024, 1, 1)
        d = date(2024 - (n_days - i) // 365, 1 + ((n_days - i) % 365) // 30 % 12, max(1, (n_days - i) % 28))
        records.append(
            OHLCV(
                ticker=ticker,
                date=d,
                open=price - Decimal("5"),
                high=price + Decimal("10"),
                low=price - Decimal("10"),
                close=price,
                volume=1_000_000,
            )
        )
    return records


def _make_sequential_series(ticker, n_days, base_price, daily_change):
    """Generate n_days of OHLCV with sequential dates and daily price change."""
    records = []
    for i in range(n_days):
        price = base_price + Decimal(str(i)) * daily_change
        d = date(2023, 1, 1)
        day_offset = i
        year = 2023 + day_offset // 365
        remainder = day_offset % 365
        month = 1 + remainder // 30
        day = 1 + remainder % 28
        if month > 12:
            month = 12
        records.append(
            OHLCV(
                ticker=ticker,
                date=date(year, month, day),
                open=price - Decimal("2"),
                high=price + Decimal("5"),
                low=price - Decimal("5"),
                close=price,
                volume=1_000_000,
            )
        )
    return records


class TestMomentumFactor:
    def test_insufficient_data_returns_default(self, ticker):
        records = _make_sequential_series(ticker, 10, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, None)
        assert scores.momentum_score == Decimal(50)

    def test_strong_momentum_scores_high(self, ticker):
        records = _make_sequential_series(ticker, 260, Decimal("100"), Decimal("2"))
        scores = compute_factor_scores(ticker, records, None)
        assert scores.momentum_score >= Decimal(65)


class TestQualityFactor:
    def test_no_fundamentals_returns_default(self, ticker):
        records = _make_sequential_series(ticker, 30, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, None)
        assert scores.quality_score == Decimal(50)

    def test_high_quality_scores_high(self, ticker):
        fundamentals = FundamentalData(
            ticker=ticker,
            as_of_date=date.today(),
            profit_growth_3yr=Decimal("0.25"),
            operating_profit_margin=Decimal("0.22"),
            roe=Decimal("0.25"),
        )
        records = _make_sequential_series(ticker, 30, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, fundamentals)
        assert scores.quality_score >= Decimal(80)

    def test_poor_quality_scores_low(self, ticker):
        fundamentals = FundamentalData(
            ticker=ticker,
            as_of_date=date.today(),
            profit_growth_3yr=Decimal("-0.10"),
            operating_profit_margin=Decimal("0.03"),
            roe=Decimal("0.03"),
        )
        records = _make_sequential_series(ticker, 30, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, fundamentals)
        assert scores.quality_score <= Decimal(30)


class TestValueFactor:
    def test_deep_value_scores_high(self, ticker):
        fundamentals = FundamentalData(
            ticker=ticker,
            as_of_date=date.today(),
            pe_ratio=Decimal("8"),
            pb_ratio=Decimal("1.2"),
            ev_ebitda=Decimal("6"),
        )
        records = _make_sequential_series(ticker, 30, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, fundamentals)
        assert scores.value_score >= Decimal(80)

    def test_overvalued_scores_low(self, ticker):
        fundamentals = FundamentalData(
            ticker=ticker,
            as_of_date=date.today(),
            pe_ratio=Decimal("45"),
            pb_ratio=Decimal("8"),
            ev_ebitda=Decimal("30"),
        )
        records = _make_sequential_series(ticker, 30, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, fundamentals)
        assert scores.value_score <= Decimal(30)


class TestCompositeFactorScore:
    def test_composite_is_average_of_pillars(self, ticker):
        records = _make_sequential_series(ticker, 30, Decimal("100"), Decimal("1"))
        scores = compute_factor_scores(ticker, records, None)
        expected = (scores.momentum_score + scores.quality_score + scores.value_score) / 3
        assert scores.composite == expected
