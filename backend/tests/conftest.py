"""Shared test fixtures."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.core.types import DataQualityFlag, Exchange, Market, Ticker
from app.domain.market_data.models import OHLCV, LiquidityProfile


@pytest.fixture
def sample_ticker() -> Ticker:
    return Ticker(symbol="RELIANCE", exchange=Exchange.NSE, market=Market.INDIA)


@pytest.fixture
def sample_ohlcv(sample_ticker: Ticker) -> OHLCV:
    return OHLCV(
        ticker=sample_ticker,
        date=date(2024, 1, 15),
        open=Decimal("2500.00"),
        high=Decimal("2550.00"),
        low=Decimal("2480.00"),
        close=Decimal("2530.00"),
        volume=5_000_000,
        available_at=datetime(2024, 1, 15, 15, 30),
    )


@pytest.fixture
def sample_ohlcv_series(sample_ticker: Ticker) -> list[OHLCV]:
    base_price = Decimal("2500")
    records = []
    for i in range(30):
        d = date(2024, 1, 1 + i) if i < 28 else date(2024, 2, i - 27)
        price = base_price + Decimal(str(i * 5))
        records.append(
            OHLCV(
                ticker=sample_ticker,
                date=d,
                open=price - Decimal("10"),
                high=price + Decimal("20"),
                low=price - Decimal("15"),
                close=price,
                volume=1_000_000 + i * 50_000,
            )
        )
    return records


@pytest.fixture
def liquid_profile(sample_ticker: Ticker) -> LiquidityProfile:
    return LiquidityProfile(
        ticker=sample_ticker,
        avg_daily_volume_20d=5_000_000,
        avg_daily_value_20d=Decimal("12_500_000_000"),
        market_cap_category="large",
        liquidity_score=Decimal("100"),
    )


@pytest.fixture
def illiquid_profile(sample_ticker: Ticker) -> LiquidityProfile:
    return LiquidityProfile(
        ticker=sample_ticker,
        avg_daily_volume_20d=1000,
        avg_daily_value_20d=Decimal("50_000"),
        market_cap_category="micro",
        liquidity_score=Decimal("5"),
    )
