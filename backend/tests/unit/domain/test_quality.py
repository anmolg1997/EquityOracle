"""Tests for data quality gate — pure domain logic."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.core.types import DataQualityFlag, Exchange, Market, Ticker
from app.domain.market_data.models import OHLCV
from app.domain.market_data.quality import (
    check_cross_source_divergence,
    check_freshness,
    check_outlier,
    check_split_or_corporate_action,
    check_delisted,
    run_quality_gate,
)


@pytest.fixture
def ticker():
    return Ticker(symbol="TCS", exchange=Exchange.NSE, market=Market.INDIA)


def _make_ohlcv(ticker, d, close, volume=1_000_000, open_=None):
    return OHLCV(
        ticker=ticker,
        date=d,
        open=open_ or close - Decimal("5"),
        high=close + Decimal("10"),
        low=close - Decimal("15"),
        close=close,
        volume=volume,
    )


class TestFreshnessCheck:
    def test_fresh_data_passes(self, ticker):
        record = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3500"))
        result = check_freshness(record, reference_date=date(2024, 3, 18))
        assert result is None  # Monday referencing Friday is OK

    def test_stale_data_flagged(self, ticker):
        record = _make_ohlcv(ticker, date(2024, 3, 10), Decimal("3500"))
        result = check_freshness(record, reference_date=date(2024, 3, 18))
        assert result is not None
        assert result.flag == DataQualityFlag.STALE

    def test_none_record_is_stale(self):
        result = check_freshness(None, reference_date=date(2024, 3, 18))
        assert result is not None
        assert result.flag == DataQualityFlag.STALE


class TestSplitDetection:
    def test_normal_price_movement(self, ticker):
        yesterday = _make_ohlcv(ticker, date(2024, 3, 14), Decimal("3500"))
        today = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3550"))
        result = check_split_or_corporate_action(today, yesterday)
        assert result is None

    def test_split_detected(self, ticker):
        yesterday = _make_ohlcv(ticker, date(2024, 3, 14), Decimal("3500"), volume=1_000_000)
        today = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("1750"), volume=1_500_000)
        result = check_split_or_corporate_action(today, yesterday)
        assert result is not None
        assert result.flag == DataQualityFlag.SPLIT_SUSPECTED

    def test_crash_not_flagged_as_split(self, ticker):
        """Real crash: price drops + volume spikes 10x."""
        yesterday = _make_ohlcv(ticker, date(2024, 3, 14), Decimal("3500"), volume=1_000_000)
        today = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("2500"), volume=10_000_000)
        result = check_split_or_corporate_action(today, yesterday)
        assert result is None


class TestOutlierDetection:
    def test_normal_return_passes(self, ticker):
        record = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3500"), open_=Decimal("3480"))
        hist_returns = [Decimal(str(0.003 + i * 0.0002)) for i in range(50)]
        result = check_outlier(record, hist_returns)
        assert result is None

    def test_extreme_return_flagged(self, ticker):
        record = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("5000"), open_=Decimal("3500"))
        hist_returns = [Decimal(str(0.003 + i * 0.0002)) for i in range(50)]
        result = check_outlier(record, hist_returns)
        assert result is not None
        assert result.flag == DataQualityFlag.OUTLIER


class TestCrossSourceDivergence:
    def test_matching_sources(self, ticker):
        primary = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3500"))
        secondary = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3501"))
        result = check_cross_source_divergence(primary, secondary)
        assert result is None

    def test_divergent_sources(self, ticker):
        primary = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3500"))
        secondary = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("3600"))
        result = check_cross_source_divergence(primary, secondary)
        assert result is not None
        assert result.flag == DataQualityFlag.DIVERGENT


class TestDelistedDetection:
    def test_active_stock(self, ticker):
        records = [_make_ohlcv(ticker, date(2024, 3, i + 1), Decimal("100"), volume=1000) for i in range(15)]
        result = check_delisted(records)
        assert result is None

    def test_delisted_stock(self, ticker):
        records = [_make_ohlcv(ticker, date(2024, 3, i + 1), Decimal("100"), volume=0) for i in range(15)]
        result = check_delisted(records)
        assert result is not None
        assert result.flag == DataQualityFlag.DELISTED


class TestQualityGateBatch:
    def test_clean_batch(self, ticker):
        records = [
            _make_ohlcv(ticker, date(2024, 3, i + 1), Decimal("3500") + Decimal(str(i * 2)))
            for i in range(5)
        ]
        report = run_quality_gate(records)
        assert report.total_records == 5
        assert report.flagged == 0
