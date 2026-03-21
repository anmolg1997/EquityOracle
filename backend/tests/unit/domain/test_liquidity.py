"""Tests for liquidity scoring and impact estimation."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, Ticker
from app.domain.market_data.liquidity import (
    compute_liquidity_profile,
    estimate_market_impact,
    max_position_by_liquidity,
    passes_liquidity_filter,
)
from app.domain.market_data.models import LiquidityProfile, OHLCV


@pytest.fixture
def ticker():
    return Ticker(symbol="INFY", exchange=Exchange.NSE, market=Market.INDIA)


def _make_ohlcv(ticker, day, close, volume):
    return OHLCV(
        ticker=ticker,
        date=date(2024, 3, day),
        open=close,
        high=close + Decimal("5"),
        low=close - Decimal("5"),
        close=close,
        volume=volume,
    )


class TestLiquidityProfile:
    def test_large_cap_classification(self, ticker):
        records = [_make_ohlcv(ticker, i + 1, Decimal("1500"), 5_000_000) for i in range(20)]
        profile = compute_liquidity_profile(ticker, records)
        assert profile.market_cap_category == "large"
        assert profile.liquidity_score >= Decimal("90")

    def test_small_cap_classification(self, ticker):
        records = [_make_ohlcv(ticker, i + 1, Decimal("100"), 100_000) for i in range(20)]
        profile = compute_liquidity_profile(ticker, records)
        assert profile.market_cap_category == "small"

    def test_empty_history(self, ticker):
        profile = compute_liquidity_profile(ticker, [])
        assert profile.avg_daily_volume_20d == 0
        assert not profile.is_tradeable


class TestLiquidityFilter:
    def test_passes_min_threshold(self, liquid_profile):
        assert passes_liquidity_filter(liquid_profile, Decimal("1_000_000"))

    def test_fails_min_threshold(self, illiquid_profile):
        assert not passes_liquidity_filter(illiquid_profile, Decimal("1_000_000"))


class TestMarketImpact:
    def test_small_order_low_impact(self, liquid_profile):
        impact = estimate_market_impact(liquid_profile, Decimal("10_000_000"))
        assert impact.is_feasible
        assert impact.estimated_slippage_pct < Decimal("0.1")

    def test_large_order_high_impact(self):
        profile = LiquidityProfile(
            ticker=Ticker("SMALL", Exchange.NSE, Market.INDIA),
            avg_daily_volume_20d=10_000,
            avg_daily_value_20d=Decimal("1_000_000"),
            market_cap_category="small",
            liquidity_score=Decimal("10"),
        )
        impact = estimate_market_impact(profile, Decimal("200_000"))
        assert not impact.is_feasible
        assert impact.warning != ""
        assert impact.participation_rate > Decimal("10")

    def test_zero_liquidity(self, ticker):
        profile = LiquidityProfile(ticker=ticker)
        impact = estimate_market_impact(profile, Decimal("100_000"))
        assert not impact.is_feasible


class TestMaxPosition:
    def test_cap_calculation(self, liquid_profile):
        max_val = max_position_by_liquidity(liquid_profile)
        assert max_val == liquid_profile.avg_daily_value_20d * Decimal("5") / 100
