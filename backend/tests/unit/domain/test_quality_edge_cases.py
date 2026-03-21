"""Edge case tests for data quality gate."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import DataQualityFlag, Exchange, Market, Ticker
from app.domain.market_data.models import OHLCV
from app.domain.market_data.quality import (
    check_cross_source_divergence,
    check_freshness,
    check_outlier,
    check_split_or_corporate_action,
    run_quality_gate,
)


@pytest.fixture
def ticker():
    return Ticker(symbol="TEST", exchange=Exchange.NSE, market=Market.INDIA)


def _ohlcv(ticker, d, close, volume=1_000_000, open_=None):
    return OHLCV(
        ticker=ticker, date=d,
        open=open_ or close - Decimal("5"),
        high=close + Decimal("10"),
        low=close - Decimal("15"),
        close=close, volume=volume,
    )


class TestFreshnessEdgeCases:
    def test_weekend_not_stale(self, ticker):
        """Friday data checked on Monday should not be stale."""
        record = _ohlcv(ticker, date(2024, 3, 15), Decimal("100"))
        result = check_freshness(record, reference_date=date(2024, 3, 18))
        assert result is None

    def test_exactly_at_threshold(self, ticker):
        """Data at exactly max_stale_days boundary."""
        record = _ohlcv(ticker, date(2024, 3, 12), Decimal("100"))
        result = check_freshness(record, reference_date=date(2024, 3, 15), max_stale_days=3)
        assert result is None

    def test_one_past_threshold(self, ticker):
        record = _ohlcv(ticker, date(2024, 3, 8), Decimal("100"))
        result = check_freshness(record, reference_date=date(2024, 3, 15), max_stale_days=3)
        assert result is not None


class TestSplitEdgeCases:
    def test_zero_close_yesterday(self, ticker):
        yesterday = _ohlcv(ticker, date(2024, 3, 14), Decimal("0"))
        today = _ohlcv(ticker, date(2024, 3, 15), Decimal("100"))
        result = check_split_or_corporate_action(today, yesterday)
        assert result is None

    def test_exactly_at_threshold(self, ticker):
        yesterday = _ohlcv(ticker, date(2024, 3, 14), Decimal("100"), volume=1000)
        today = _ohlcv(ticker, date(2024, 3, 15), Decimal("80"), volume=1000)
        result = check_split_or_corporate_action(today, yesterday)
        assert result is not None

    def test_volume_at_threshold_no_flag(self, ticker):
        yesterday = _ohlcv(ticker, date(2024, 3, 14), Decimal("100"), volume=1000)
        today = _ohlcv(ticker, date(2024, 3, 15), Decimal("50"), volume=3000)
        result = check_split_or_corporate_action(today, yesterday)
        assert result is None


class TestOutlierEdgeCases:
    def test_insufficient_history_skips(self, ticker):
        record = _ohlcv(ticker, date(2024, 3, 15), Decimal("100"), open_=Decimal("90"))
        result = check_outlier(record, [Decimal("0.01")] * 10)
        assert result is None

    def test_zero_open_skips(self, ticker):
        record = OHLCV(
            ticker=ticker, date=date(2024, 3, 15),
            open=Decimal("0"), high=Decimal("10"),
            low=Decimal("0"), close=Decimal("5"), volume=1000,
        )
        result = check_outlier(record, [Decimal("0.01")] * 50)
        assert result is None


class TestCrossSourceEdgeCases:
    def test_zero_primary_close(self, ticker):
        primary = _ohlcv(ticker, date(2024, 3, 15), Decimal("0"))
        secondary = _ohlcv(ticker, date(2024, 3, 15), Decimal("100"))
        result = check_cross_source_divergence(primary, secondary)
        assert result is None


class TestQualityGateExtended:
    def test_multiple_tickers_in_batch(self, ticker):
        t2 = Ticker(symbol="TEST2", exchange=Exchange.NSE, market=Market.INDIA)
        records = [
            _ohlcv(ticker, date(2024, 3, i + 1), Decimal("100") + Decimal(str(i)))
            for i in range(5)
        ] + [
            _ohlcv(t2, date(2024, 3, i + 1), Decimal("200") + Decimal(str(i)))
            for i in range(5)
        ]
        report = run_quality_gate(records)
        assert report.total_records == 10

    def test_split_detected_in_batch(self, ticker):
        records = [
            _ohlcv(ticker, date(2024, 3, 1), Decimal("1000"), volume=100_000),
            _ohlcv(ticker, date(2024, 3, 2), Decimal("500"), volume=100_000),
        ]
        report = run_quality_gate(records)
        assert report.flagged > 0
        assert any(c.flag == DataQualityFlag.SPLIT_SUSPECTED for c in report.checks)
