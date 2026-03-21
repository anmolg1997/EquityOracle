"""Data provider factory — maps market to adapter chain with fallbacks."""

from __future__ import annotations

from app.core.types import Market
from app.domain.market_data.ports import MarketDataProvider
from app.infrastructure.data_providers.india import IndiaDataProvider
from app.infrastructure.data_providers.us import USDataProvider
from app.infrastructure.data_providers.global_screener import GlobalScreenerProvider
from app.infrastructure.data_providers.resilience import ResilientDataProvider


def create_data_provider(market: Market) -> MarketDataProvider:
    """Create a resilient data provider for the given market."""
    if market == Market.INDIA:
        return ResilientDataProvider(providers=[IndiaDataProvider()])

    if market == Market.US:
        return ResilientDataProvider(providers=[USDataProvider()])

    return ResilientDataProvider(providers=[GlobalScreenerProvider(), USDataProvider()])
