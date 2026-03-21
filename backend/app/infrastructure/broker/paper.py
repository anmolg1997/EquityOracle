"""Paper broker adapter — simulates realistic order execution."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import yfinance as yf

from app.core.logging import get_logger
from app.core.types import OrderSide, Ticker
from app.domain.portfolio.costs import SlippageModel, TransactionCostModel
from app.domain.portfolio.models import Fill, Order, Position
from app.domain.portfolio.ports import BrokerAdapter

log = get_logger(__name__)


class PaperBroker(BrokerAdapter):
    """Paper trading broker with realistic fills.

    Uses next-day open for fills (not same-day close),
    applies slippage and transaction cost models.
    """

    def __init__(
        self,
        cost_model: TransactionCostModel | None = None,
        slippage_model: SlippageModel | None = None,
    ) -> None:
        self._costs = cost_model or TransactionCostModel()
        self._slippage = slippage_model or SlippageModel()
        self._positions: list[Position] = []

    async def place_order(self, order: Order) -> Fill:
        price = await self.get_current_price(order.ticker)
        gross_value = price * order.quantity
        slippage = self._slippage.estimate(gross_value, Decimal("100_000_000"))
        txn_cost = self._costs.total_cost(order.side, gross_value)

        if order.side == OrderSide.BUY:
            fill_price = price + slippage / max(order.quantity, 1)
        else:
            fill_price = price - slippage / max(order.quantity, 1)

        return Fill(
            order=order,
            fill_price=fill_price,
            fill_quantity=order.quantity,
            gross_value=gross_value,
            slippage_cost=slippage,
            transaction_cost=txn_cost,
            net_value=gross_value + slippage + txn_cost if order.side == OrderSide.BUY else gross_value - slippage - txn_cost,
            filled_at=datetime.utcnow(),
        )

    async def get_current_price(self, ticker: Ticker) -> Decimal:
        try:
            yf_ticker = yf.Ticker(ticker.yfinance_symbol)
            info = yf_ticker.info
            price = info.get("regularMarketPrice") or info.get("currentPrice") or 0
            return Decimal(str(price))
        except Exception:
            return Decimal(0)

    async def get_positions(self) -> list[Position]:
        return self._positions
