"""Event-driven portfolio engine — order -> risk check -> fill -> position update."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.logging import get_logger
from app.core.types import OrderSide
from app.domain.portfolio.costs import SlippageModel, TaxModel, TransactionCostModel
from app.domain.portfolio.models import Fill, Order, OrderStatus, Portfolio, Position

log = get_logger(__name__)


class PortfolioEngine:
    """Processes orders through the full lifecycle with realistic costs."""

    def __init__(
        self,
        portfolio: Portfolio,
        cost_model: TransactionCostModel | None = None,
        slippage_model: SlippageModel | None = None,
        tax_model: TaxModel | None = None,
    ) -> None:
        self._portfolio = portfolio
        self._costs = cost_model or TransactionCostModel()
        self._slippage = slippage_model or SlippageModel()
        self._tax = tax_model or TaxModel()

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio

    def process_buy(
        self,
        order: Order,
        fill_price: Decimal,
        avg_daily_volume_value: Decimal = Decimal("100_000_000"),
        market_cap_category: str = "mid",
    ) -> Fill:
        """Process a buy order with realistic costs."""
        gross_value = fill_price * order.quantity

        slippage = self._slippage.estimate(gross_value, avg_daily_volume_value, market_cap_category)
        effective_price = fill_price + slippage / order.quantity
        txn_cost = self._costs.total_cost(OrderSide.BUY, gross_value)

        net_value = gross_value + slippage + txn_cost

        if net_value > self._portfolio.cash:
            log.warning("insufficient_cash", required=str(net_value), available=str(self._portfolio.cash))
            raise ValueError(f"Insufficient cash: need {net_value}, have {self._portfolio.cash}")

        self._portfolio.cash -= net_value

        position = Position(
            ticker=order.ticker,
            quantity=order.quantity,
            entry_price=effective_price,
            entry_date=date.today(),
            current_price=fill_price,
            entry_costs=txn_cost,
            slippage_total=slippage,
            recommendation_id=order.recommendation_id,
        )
        self._portfolio.positions.append(position)

        return Fill(
            order=order,
            fill_price=effective_price,
            fill_quantity=order.quantity,
            gross_value=gross_value,
            slippage_cost=slippage,
            transaction_cost=txn_cost,
            net_value=net_value,
        )

    def process_sell(
        self,
        position: Position,
        sell_price: Decimal,
        avg_daily_volume_value: Decimal = Decimal("100_000_000"),
        market_cap_category: str = "mid",
    ) -> Fill:
        """Close a position with realistic costs and tax estimation."""
        gross_value = sell_price * position.quantity

        slippage = self._slippage.estimate(gross_value, avg_daily_volume_value, market_cap_category)
        effective_price = sell_price - slippage / position.quantity
        txn_cost = self._costs.total_cost(OrderSide.SELL, gross_value)

        net_proceeds = gross_value - slippage - txn_cost

        # Tax estimation
        gross_gain = (effective_price - position.entry_price) * position.quantity
        tax = self._tax.compute_tax(gross_gain, position.hold_days)

        position.exit_price = effective_price
        position.exit_date = date.today()
        position.is_open = False
        position.exit_costs = txn_cost
        position.slippage_total += slippage
        position.estimated_tax = tax

        self._portfolio.cash += net_proceeds

        order = Order(ticker=position.ticker, side=OrderSide.SELL, quantity=position.quantity)
        return Fill(
            order=order,
            fill_price=effective_price,
            fill_quantity=position.quantity,
            gross_value=gross_value,
            slippage_cost=slippage,
            transaction_cost=txn_cost,
            net_value=net_proceeds,
        )

    def update_prices(self, prices: dict[str, Decimal]) -> None:
        """Update current prices for all open positions."""
        for pos in self._portfolio.open_positions:
            key = str(pos.ticker)
            if key in prices:
                pos.current_price = prices[key]
