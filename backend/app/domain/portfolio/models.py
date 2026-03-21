"""Pure domain models for the Portfolio bounded context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from app.core.types import OrderSide, OrderType, Ticker


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class Order:
    ticker: Ticker
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Decimal | None = None
    recommendation_id: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Fill:
    order: Order
    fill_price: Decimal
    fill_quantity: int
    gross_value: Decimal
    slippage_cost: Decimal = Decimal(0)
    transaction_cost: Decimal = Decimal(0)
    net_value: Decimal = Decimal(0)
    filled_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    ticker: Ticker
    quantity: int
    entry_price: Decimal
    entry_date: date
    current_price: Decimal = Decimal(0)
    exit_price: Decimal | None = None
    exit_date: date | None = None
    is_open: bool = True

    # Cost tracking
    entry_costs: Decimal = Decimal(0)
    exit_costs: Decimal = Decimal(0)
    slippage_total: Decimal = Decimal(0)
    estimated_tax: Decimal = Decimal(0)

    recommendation_id: int | None = None

    @property
    def gross_pnl(self) -> Decimal:
        price = self.exit_price if self.exit_price else self.current_price
        return (price - self.entry_price) * self.quantity

    @property
    def net_pnl(self) -> Decimal:
        return self.gross_pnl - self.entry_costs - self.exit_costs - self.slippage_total - self.estimated_tax

    @property
    def gross_return_pct(self) -> Decimal:
        if self.entry_price == 0:
            return Decimal(0)
        return (self.gross_pnl / (self.entry_price * self.quantity)) * 100

    @property
    def net_return_pct(self) -> Decimal:
        invested = self.entry_price * self.quantity + self.entry_costs
        if invested == 0:
            return Decimal(0)
        return (self.net_pnl / invested) * 100

    @property
    def hold_days(self) -> int:
        end = self.exit_date or date.today()
        return (end - self.entry_date).days


@dataclass
class Portfolio:
    portfolio_id: str
    positions: list[Position] = field(default_factory=list)
    cash: Decimal = Decimal("1_000_000")
    initial_capital: Decimal = Decimal("1_000_000")

    @property
    def open_positions(self) -> list[Position]:
        return [p for p in self.positions if p.is_open]

    @property
    def closed_positions(self) -> list[Position]:
        return [p for p in self.positions if not p.is_open]

    @property
    def invested_value(self) -> Decimal:
        return sum(p.current_price * p.quantity for p in self.open_positions)

    @property
    def total_value(self) -> Decimal:
        return self.cash + self.invested_value

    @property
    def gross_pnl(self) -> Decimal:
        return sum(p.gross_pnl for p in self.positions)

    @property
    def net_pnl(self) -> Decimal:
        return sum(p.net_pnl for p in self.positions)

    @property
    def total_return_pct(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal(0)
        return ((self.total_value - self.initial_capital) / self.initial_capital) * 100


@dataclass
class PerformanceMetrics:
    total_return_pct: Decimal = Decimal(0)
    gross_return_pct: Decimal = Decimal(0)
    net_return_pct: Decimal = Decimal(0)
    sharpe_ratio: Decimal = Decimal(0)
    sortino_ratio: Decimal = Decimal(0)
    max_drawdown_pct: Decimal = Decimal(0)
    win_rate: Decimal = Decimal(0)
    profit_factor: Decimal = Decimal(0)
    total_trades: int = 0
    total_costs: Decimal = Decimal(0)
    total_tax: Decimal = Decimal(0)
    total_slippage: Decimal = Decimal(0)
    benchmark_return_pct: Decimal = Decimal(0)
    alpha: Decimal = Decimal(0)
