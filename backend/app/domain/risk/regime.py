"""Market regime detection — bull/bear/sideways classification."""

from __future__ import annotations

from decimal import Decimal

from app.core.types import MarketRegime
from app.domain.market_data.models import MarketBreadth, OHLCV


def detect_regime(
    index_ohlcv: list[OHLCV],
    breadth: MarketBreadth | None = None,
) -> MarketRegime:
    """Detect current market regime from index data and breadth."""
    if len(index_ohlcv) < 200:
        return MarketRegime.UNCERTAIN

    sorted_data = sorted(index_ohlcv, key=lambda r: r.date)
    current = sorted_data[-1].close
    sma_50 = sum(r.close for r in sorted_data[-50:]) / 50
    sma_200 = sum(r.close for r in sorted_data[-200:]) / 200

    # Price above both SMAs = bull
    if current > sma_50 > sma_200:
        return MarketRegime.BULL

    # Price below both SMAs = bear
    if current < sma_50 < sma_200:
        return MarketRegime.BEAR

    # Breadth-based refinement
    if breadth:
        if breadth.above_200_dma_pct > Decimal(60):
            return MarketRegime.BULL
        if breadth.above_200_dma_pct < Decimal(30):
            return MarketRegime.BEAR

    return MarketRegime.SIDEWAYS
