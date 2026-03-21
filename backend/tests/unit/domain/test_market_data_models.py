"""Tests for market data domain models — OHLCV properties, InstitutionalFlow, MarketBreadth."""

from datetime import date
from decimal import Decimal

from app.core.types import Exchange, Market, Ticker
from app.domain.market_data.models import (
    InstitutionalFlow,
    LiquidityProfile,
    MarketBreadth,
    OHLCV,
)


class TestOHLCV:
    def test_typical_price(self):
        ohlcv = OHLCV(
            ticker=Ticker("A", Exchange.NSE, Market.INDIA),
            date=date.today(), open=Decimal("100"),
            high=Decimal("110"), low=Decimal("90"),
            close=Decimal("105"), volume=1000,
        )
        assert ohlcv.typical_price == (Decimal("110") + Decimal("90") + Decimal("105")) / 3

    def test_daily_return_pct(self):
        ohlcv = OHLCV(
            ticker=Ticker("A", Exchange.NSE, Market.INDIA),
            date=date.today(), open=Decimal("100"),
            high=Decimal("110"), low=Decimal("90"),
            close=Decimal("110"), volume=1000,
        )
        assert ohlcv.daily_return_pct == Decimal("10")

    def test_daily_return_none_when_open_zero(self):
        ohlcv = OHLCV(
            ticker=Ticker("A", Exchange.NSE, Market.INDIA),
            date=date.today(), open=Decimal("0"),
            high=Decimal("10"), low=Decimal("0"),
            close=Decimal("5"), volume=1000,
        )
        assert ohlcv.daily_return_pct is None

    def test_daily_value(self):
        ohlcv = OHLCV(
            ticker=Ticker("A", Exchange.NSE, Market.INDIA),
            date=date.today(), open=Decimal("100"),
            high=Decimal("110"), low=Decimal("90"),
            close=Decimal("100"), volume=5000,
        )
        assert ohlcv.daily_value == Decimal("500000")


class TestInstitutionalFlow:
    def test_fii_net(self):
        flow = InstitutionalFlow(
            market=Market.INDIA, date=date.today(),
            fii_buy_value=Decimal("1000"), fii_sell_value=Decimal("600"),
        )
        assert flow.fii_net == Decimal("400")

    def test_dii_net(self):
        flow = InstitutionalFlow(
            market=Market.INDIA, date=date.today(),
            dii_buy_value=Decimal("800"), dii_sell_value=Decimal("500"),
        )
        assert flow.dii_net == Decimal("300")

    def test_total_net(self):
        flow = InstitutionalFlow(
            market=Market.INDIA, date=date.today(),
            fii_buy_value=Decimal("1000"), fii_sell_value=Decimal("600"),
            dii_buy_value=Decimal("800"), dii_sell_value=Decimal("500"),
        )
        assert flow.total_net == Decimal("700")


class TestMarketBreadth:
    def test_advance_decline_ratio(self):
        breadth = MarketBreadth(
            market=Market.INDIA, date=date.today(),
            advances=300, declines=100,
        )
        assert breadth.advance_decline_ratio == Decimal("3")

    def test_advance_decline_ratio_zero_declines(self):
        breadth = MarketBreadth(
            market=Market.INDIA, date=date.today(),
            advances=300, declines=0,
        )
        assert breadth.advance_decline_ratio == Decimal("999")

    def test_breadth_thrust(self):
        breadth = MarketBreadth(
            market=Market.INDIA, date=date.today(),
            advances=800, declines=100, unchanged=100,
        )
        assert breadth.breadth_thrust

    def test_no_breadth_thrust(self):
        breadth = MarketBreadth(
            market=Market.INDIA, date=date.today(),
            advances=400, declines=400, unchanged=200,
        )
        assert not breadth.breadth_thrust


class TestLiquidityProfile:
    def test_is_tradeable(self):
        lp = LiquidityProfile(
            ticker=Ticker("A", Exchange.NSE, Market.INDIA),
            avg_daily_value_20d=Decimal("1000"),
        )
        assert lp.is_tradeable

    def test_not_tradeable(self):
        lp = LiquidityProfile(ticker=Ticker("A", Exchange.NSE, Market.INDIA))
        assert not lp.is_tradeable
