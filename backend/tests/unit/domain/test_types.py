"""Tests for core value objects — Ticker, DateRange, enums, PipelineRunContext."""

from datetime import date

import pytest

from app.core.types import (
    CircuitBreakerState,
    DateRange,
    Exchange,
    Market,
    PipelineRunContext,
    Ticker,
    TimeHorizon,
    new_correlation_id,
)


class TestTicker:
    def test_yfinance_symbol_nse(self):
        t = Ticker(symbol="RELIANCE", exchange=Exchange.NSE, market=Market.INDIA)
        assert t.yfinance_symbol == "RELIANCE.NS"

    def test_yfinance_symbol_bse(self):
        t = Ticker(symbol="TCS", exchange=Exchange.BSE, market=Market.INDIA)
        assert t.yfinance_symbol == "TCS.BO"

    def test_yfinance_symbol_nyse(self):
        t = Ticker(symbol="AAPL", exchange=Exchange.NYSE, market=Market.US)
        assert t.yfinance_symbol == "AAPL"

    def test_str_representation(self):
        t = Ticker(symbol="INFY", exchange=Exchange.NSE, market=Market.INDIA)
        assert str(t) == "INFY:NSE"

    def test_ticker_is_hashable(self):
        t1 = Ticker(symbol="A", exchange=Exchange.NSE, market=Market.INDIA)
        t2 = Ticker(symbol="A", exchange=Exchange.NSE, market=Market.INDIA)
        assert t1 == t2
        assert hash(t1) == hash(t2)
        assert len({t1, t2}) == 1

    def test_ticker_frozen(self):
        t = Ticker(symbol="A", exchange=Exchange.NSE, market=Market.INDIA)
        with pytest.raises(AttributeError):
            t.symbol = "B"


class TestDateRange:
    def test_valid_range(self):
        dr = DateRange(start=date(2024, 1, 1), end=date(2024, 6, 1))
        assert dr.start < dr.end

    def test_same_start_end(self):
        dr = DateRange(start=date(2024, 1, 1), end=date(2024, 1, 1))
        assert dr.start == dr.end

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError, match="must be <="):
            DateRange(start=date(2024, 6, 1), end=date(2024, 1, 1))


class TestCorrelationId:
    def test_unique_ids(self):
        ids = {new_correlation_id() for _ in range(100)}
        assert len(ids) == 100

    def test_length(self):
        cid = new_correlation_id()
        assert len(cid) == 16


class TestPipelineRunContext:
    def test_defaults(self):
        ctx = PipelineRunContext()
        assert ctx.market == Market.INDIA
        assert ctx.correlation_id
        assert ctx.run_date == date.today()
