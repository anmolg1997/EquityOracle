"""Alpaca adapter (stub — ready for US live trading)."""

from __future__ import annotations

from decimal import Decimal

from app.core.logging import get_logger
from app.core.types import Ticker
from app.domain.portfolio.models import Fill, Order, Position
from app.domain.portfolio.ports import BrokerAdapter

log = get_logger(__name__)


class AlpacaBroker(BrokerAdapter):
    """Stub for Alpaca API integration."""

    def __init__(self, api_key: str = "", secret_key: str = "") -> None:
        self._api_key = api_key
        self._secret_key = secret_key

    async def place_order(self, order: Order) -> Fill:
        raise NotImplementedError("Alpaca integration not yet implemented — use paper broker")

    async def get_current_price(self, ticker: Ticker) -> Decimal:
        raise NotImplementedError("Alpaca integration not yet implemented")

    async def get_positions(self) -> list[Position]:
        return []
