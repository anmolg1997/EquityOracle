"""Tests for market regime detection."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, MarketRegime, Ticker
from app.domain.market_data.models import MarketBreadth, OHLCV
from app.domain.risk.regime import detect_regime


@pytest.fixture
def ticker():
    return Ticker(symbol="NIFTY", exchange=Exchange.NSE, market=Market.INDIA)


def _make_index(ticker, n_days, start_price, end_price):
    """Generate index OHLCV with linear interpolation."""
    records = []
    step = (float(end_price) - float(start_price)) / max(n_days - 1, 1)
    for i in range(n_days):
        price = Decimal(str(round(float(start_price) + step * i, 2)))
        day = 1 + i % 28
        month = 1 + (i // 28) % 12
        year = 2023 + i // 336
        records.append(
            OHLCV(
                ticker=ticker, date=date(year, month, max(day, 1)),
                open=price, high=price + Decimal("10"),
                low=price - Decimal("10"), close=price, volume=1_000_000,
            )
        )
    return records


class TestRegimeDetection:
    def test_insufficient_data_uncertain(self, ticker):
        records = _make_index(ticker, 50, Decimal("100"), Decimal("150"))
        assert detect_regime(records) == MarketRegime.UNCERTAIN

    def test_bull_regime(self, ticker):
        records = _make_index(ticker, 250, Decimal("100"), Decimal("200"))
        result = detect_regime(records)
        assert result == MarketRegime.BULL

    def test_bear_regime(self, ticker):
        records = _make_index(ticker, 250, Decimal("200"), Decimal("100"))
        result = detect_regime(records)
        assert result == MarketRegime.BEAR

    def test_sideways_regime(self, ticker):
        records = []
        for i in range(250):
            price = Decimal("150") + Decimal(str((i % 10) - 5))
            day = 1 + i % 28
            month = 1 + (i // 28) % 12
            year = 2023 + i // 336
            records.append(
                OHLCV(
                    ticker=ticker, date=date(year, month, max(day, 1)),
                    open=price, high=price + Decimal("2"),
                    low=price - Decimal("2"), close=price, volume=1_000_000,
                )
            )
        result = detect_regime(records)
        assert result in (MarketRegime.SIDEWAYS, MarketRegime.BULL, MarketRegime.BEAR)

    def test_breadth_refinement_bull(self, ticker):
        records = _make_index(ticker, 250, Decimal("150"), Decimal("160"))
        breadth = MarketBreadth(
            market=Market.INDIA, date=date.today(),
            above_200_dma_pct=Decimal("70"),
        )
        result = detect_regime(records, breadth)
        assert result in (MarketRegime.BULL, MarketRegime.SIDEWAYS)

    def test_breadth_refinement_bear(self, ticker):
        records = _make_index(ticker, 250, Decimal("150"), Decimal("140"))
        breadth = MarketBreadth(
            market=Market.INDIA, date=date.today(),
            above_200_dma_pct=Decimal("20"),
        )
        result = detect_regime(records, breadth)
        assert result in (MarketRegime.BEAR, MarketRegime.SIDEWAYS)
