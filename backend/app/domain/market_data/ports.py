"""Port interfaces for the Market Data bounded context.

These ABCs define the contracts that infrastructure adapters must implement.
The domain layer depends only on these abstractions, never on concrete adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.core.types import Market, Ticker
from app.domain.market_data.models import (
    DataProviderHealth,
    FundamentalData,
    InsiderDeal,
    InstitutionalFlow,
    LiquidityProfile,
    MarketBreadth,
    OHLCV,
)


class MarketDataProvider(ABC):
    """Port: fetch market data from an external source."""

    @abstractmethod
    async def get_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCV]:
        ...

    @abstractmethod
    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        ...

    @abstractmethod
    async def get_insider_deals(self, ticker: Ticker, days: int = 30) -> list[InsiderDeal]:
        ...

    @abstractmethod
    async def get_institutional_flows(self, market: Market, days: int = 30) -> list[InstitutionalFlow]:
        ...

    @abstractmethod
    async def get_market_breadth(self, market: Market) -> MarketBreadth | None:
        ...

    @abstractmethod
    async def get_universe(self, market: Market) -> list[Ticker]:
        ...

    @abstractmethod
    async def health_check(self) -> DataProviderHealth:
        ...


class MarketDataRepository(ABC):
    """Port: persist and retrieve market data from storage."""

    @abstractmethod
    async def save_ohlcv_batch(self, records: list[OHLCV]) -> int:
        ...

    @abstractmethod
    async def get_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCV]:
        ...

    @abstractmethod
    async def get_latest_ohlcv(self, ticker: Ticker) -> OHLCV | None:
        ...

    @abstractmethod
    async def save_fundamentals(self, data: FundamentalData) -> None:
        ...

    @abstractmethod
    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        ...

    @abstractmethod
    async def save_insider_deals(self, deals: list[InsiderDeal]) -> int:
        ...

    @abstractmethod
    async def save_institutional_flows(self, flows: list[InstitutionalFlow]) -> int:
        ...

    @abstractmethod
    async def get_institutional_flows(self, market: Market, days: int) -> list[InstitutionalFlow]:
        ...

    @abstractmethod
    async def save_market_breadth(self, breadth: MarketBreadth) -> None:
        ...

    @abstractmethod
    async def save_liquidity_profile(self, profile: LiquidityProfile) -> None:
        ...

    @abstractmethod
    async def get_liquidity_profile(self, ticker: Ticker) -> LiquidityProfile | None:
        ...

    @abstractmethod
    async def get_universe(self, market: Market) -> list[Ticker]:
        ...
