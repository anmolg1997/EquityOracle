"""Zerodha Kite Connect adapter (stub — ready for Phase 9 implementation)."""

from __future__ import annotations

from decimal import Decimal

from app.core.logging import get_logger
from app.core.types import Ticker
from app.domain.portfolio.models import Fill, Order, Position
from app.domain.portfolio.ports import BrokerAdapter

log = get_logger(__name__)


class ZerodhaBroker(BrokerAdapter):
    """Stub for Zerodha Kite Connect integration."""

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    async def place_order(self, order: Order) -> Fill:
        raise NotImplementedError("Zerodha integration not yet implemented — use paper broker")

    async def get_current_price(self, ticker: Ticker) -> Decimal:
        raise NotImplementedError("Zerodha integration not yet implemented")

    async def get_positions(self) -> list[Position]:
        return []
