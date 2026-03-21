"""Integration test: Data quality gate -> liquidity filter -> decorrelation pipeline.

Verifies that the full data validation chain works end-to-end:
  raw data -> quality checks -> liquidity filtering -> analysis decorrelation.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import DataQualityFlag, Exchange, Market, Ticker
from app.domain.analysis.decorrelation import compute_decorrelation
from app.domain.market_data.liquidity import compute_liquidity_profile, passes_liquidity_filter
from app.domain.market_data.models import OHLCV
from app.domain.market_data.quality import run_quality_gate


@pytest.fixture
def ticker():
    return Ticker(symbol="RELIANCE", exchange=Exchange.NSE, market=Market.INDIA)


def _make_clean_series(ticker, n_days, base_price, volume):
    records = []
    for i in range(n_days):
        price = base_price + Decimal(str(i * 2))
        records.append(
            OHLCV(
                ticker=ticker,
                date=date(2024, 1, 1 + i) if i < 28 else date(2024, 2, i - 27),
                open=price - Decimal("3"),
                high=price + Decimal("5"),
                low=price - Decimal("5"),
                close=price,
                volume=volume,
            )
        )
    return records


class TestDataQualityToAnalysis:
    def test_clean_data_passes_quality_and_liquidity(self, ticker):
        """Clean data passes quality gate and liquidity filter."""
        records = _make_clean_series(ticker, 25, Decimal("2500"), 5_000_000)

        report = run_quality_gate(records)
        assert report.pass_rate > 0.9

        profile = compute_liquidity_profile(ticker, records)
        assert passes_liquidity_filter(profile, Decimal("1_000_000"))

    def test_zero_volume_fails_liquidity(self, ticker):
        """Zero-volume data is flagged and fails liquidity."""
        records = _make_clean_series(ticker, 25, Decimal("100"), 0)

        profile = compute_liquidity_profile(ticker, records)
        assert not profile.is_tradeable
        assert not passes_liquidity_filter(profile, Decimal("1_000_000"))

    def test_decorrelation_on_quality_filtered_data(self, ticker):
        """Decorrelation check works on data that passed quality gates."""
        records = _make_clean_series(ticker, 25, Decimal("2500"), 5_000_000)
        report = run_quality_gate(records)
        assert report.flagged == 0

        pillar_scores = {
            "technical": [70 + i for i in range(10)],
            "fundamental": [50 - i for i in range(10)],
            "sentiment": [60 + (i % 3) for i in range(10)],
        }
        result = compute_decorrelation(pillar_scores)
        assert result.effective_signal_count >= Decimal("2")
