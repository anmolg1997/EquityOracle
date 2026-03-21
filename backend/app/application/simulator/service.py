"""Paper trading service — manages simulated portfolio."""

from __future__ import annotations

from decimal import Decimal

from app.core.logging import get_logger
from app.core.types import OrderSide, OrderType, Ticker
from app.domain.portfolio.engine import PortfolioEngine
from app.domain.portfolio.models import Order, Portfolio, PerformanceMetrics
from app.domain.risk.circuit_breaker import CircuitBreakerService
from app.domain.risk.manager import RiskManager

log = get_logger(__name__)


class PaperTradingService:
    """Orchestrates paper trading with risk management and circuit breaker."""

    def __init__(
        self,
        engine: PortfolioEngine,
        risk_manager: RiskManager,
        circuit_breaker: CircuitBreakerService,
    ) -> None:
        self._engine = engine
        self._risk = risk_manager
        self._cb = circuit_breaker

    @property
    def portfolio(self) -> Portfolio:
        return self._engine.portfolio

    def buy(
        self,
        ticker: Ticker,
        quantity: int,
        price: Decimal,
        recommendation_id: int | None = None,
    ) -> dict:
        """Execute a paper buy order."""
        if not self._cb.allows_new_entries():
            return {"status": "rejected", "reason": f"Circuit breaker is {self._cb.state.value}"}

        order = Order(
            ticker=ticker,
            side=OrderSide.BUY,
            quantity=quantity,
            recommendation_id=recommendation_id,
        )
        order_value = price * quantity

        # Risk check
        risk_result = self._risk.validate_order(order, order_value, self._engine.portfolio)
        if not risk_result.approved:
            return {"status": "rejected", "reasons": risk_result.reasons}

        # Apply circuit breaker position size multiplier
        multiplier = self._cb.position_size_multiplier()
        adjusted_qty = int(quantity * float(multiplier))
        if adjusted_qty < 1:
            return {"status": "rejected", "reason": "Position size reduced to zero by circuit breaker"}

        order = Order(
            ticker=ticker,
            side=OrderSide.BUY,
            quantity=adjusted_qty,
            recommendation_id=recommendation_id,
        )

        try:
            fill = self._engine.process_buy(order, price)
            return {
                "status": "filled",
                "fill_price": str(fill.fill_price),
                "quantity": fill.fill_quantity,
                "gross_value": str(fill.gross_value),
                "slippage": str(fill.slippage_cost),
                "transaction_cost": str(fill.transaction_cost),
                "net_value": str(fill.net_value),
            }
        except ValueError as e:
            return {"status": "rejected", "reason": str(e)}

    def sell(self, ticker: Ticker, price: Decimal) -> dict:
        """Close an open position."""
        positions = [p for p in self._engine.portfolio.open_positions if p.ticker == ticker]
        if not positions:
            return {"status": "rejected", "reason": "No open position found"}

        position = positions[0]
        fill = self._engine.process_sell(position, price)

        return {
            "status": "filled",
            "fill_price": str(fill.fill_price),
            "gross_pnl": str(position.gross_pnl),
            "net_pnl": str(position.net_pnl),
            "slippage": str(fill.slippage_cost),
            "transaction_cost": str(fill.transaction_cost),
            "estimated_tax": str(position.estimated_tax),
        }

    def compute_performance(self) -> PerformanceMetrics:
        """Compute gross and net performance metrics."""
        portfolio = self._engine.portfolio
        closed = portfolio.closed_positions

        if not closed:
            return PerformanceMetrics(total_trades=0)

        wins = [p for p in closed if p.net_pnl > 0]
        losses = [p for p in closed if p.net_pnl <= 0]

        total_costs = sum(p.entry_costs + p.exit_costs for p in closed)
        total_slippage = sum(p.slippage_total for p in closed)
        total_tax = sum(p.estimated_tax for p in closed)

        gross_profits = sum(p.gross_pnl for p in wins) if wins else Decimal(0)
        gross_losses = abs(sum(p.gross_pnl for p in losses)) if losses else Decimal(1)

        return PerformanceMetrics(
            total_return_pct=portfolio.total_return_pct,
            gross_return_pct=portfolio.gross_pnl / portfolio.initial_capital * 100 if portfolio.initial_capital else Decimal(0),
            net_return_pct=portfolio.net_pnl / portfolio.initial_capital * 100 if portfolio.initial_capital else Decimal(0),
            win_rate=Decimal(str(len(wins) / len(closed))) if closed else Decimal(0),
            profit_factor=gross_profits / gross_losses if gross_losses > 0 else Decimal(0),
            total_trades=len(closed),
            total_costs=total_costs,
            total_tax=total_tax,
            total_slippage=total_slippage,
        )
