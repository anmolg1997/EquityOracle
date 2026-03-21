"""Port interfaces for the Portfolio bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.core.types import Ticker
from app.domain.portfolio.models import Fill, Order, Position


class BrokerAdapter(ABC):
    """Port: execute orders (paper or real)."""

    @abstractmethod
    async def place_order(self, order: Order) -> Fill:
        ...

    @abstractmethod
    async def get_current_price(self, ticker: Ticker) -> Decimal:
        ...

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        ...


class PortfolioRepository(ABC):
    """Port: persist portfolio state."""

    @abstractmethod
    async def save_position(self, position: Position, portfolio_id: str) -> None:
        ...

    @abstractmethod
    async def get_positions(self, portfolio_id: str, open_only: bool = True) -> list[Position]:
        ...

    @abstractmethod
    async def update_position(self, position: Position, portfolio_id: str) -> None:
        ...
