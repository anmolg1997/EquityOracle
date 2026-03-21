"""Integration test: Portfolio engine + risk manager + circuit breaker flow.

Tests the real interaction: risk check -> buy -> price update -> sell -> PnL verification.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import CircuitBreakerState, Exchange, Market, OrderSide, Ticker
from app.domain.portfolio.engine import PortfolioEngine
from app.domain.portfolio.models import Order, Portfolio
from app.domain.risk.circuit_breaker import CircuitBreakerService
from app.domain.risk.manager import RiskManager


@pytest.fixture
def ticker():
    return Ticker(symbol="TCS", exchange=Exchange.NSE, market=Market.INDIA)


@pytest.fixture
def portfolio():
    return Portfolio(portfolio_id="integration_test", cash=Decimal("1_000_000"))


class TestPortfolioIntegration:
    def test_full_buy_sell_cycle(self, ticker, portfolio):
        """Buy -> update price -> sell -> verify PnL."""
        engine = PortfolioEngine(portfolio)

        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        buy_fill = engine.process_buy(order, fill_price=Decimal("3500"))

        assert len(portfolio.open_positions) == 1
        assert portfolio.cash < Decimal("1_000_000")

        engine.update_prices({str(ticker): Decimal("3800")})
        pos = portfolio.open_positions[0]
        assert pos.current_price == Decimal("3800")
        assert pos.gross_pnl > 0

        sell_fill = engine.process_sell(pos, sell_price=Decimal("3800"))
        assert len(portfolio.open_positions) == 0
        assert not pos.is_open

    def test_risk_check_then_buy(self, ticker, portfolio):
        """Risk manager validates before engine processes."""
        risk_mgr = RiskManager(max_position_pct=Decimal("0.10"))
        engine = PortfolioEngine(portfolio)

        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        order_value = Decimal("50_000")

        result = risk_mgr.validate_order(order, order_value, portfolio)
        assert result.approved

        engine.process_buy(order, fill_price=Decimal("500"))
        assert len(portfolio.open_positions) == 1

    def test_risk_rejects_oversized_position(self, ticker, portfolio):
        """Risk manager prevents oversized positions."""
        risk_mgr = RiskManager(max_position_pct=Decimal("0.10"))
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("200_000"), portfolio)
        assert not result.approved

    def test_circuit_breaker_blocks_new_entries(self, ticker, portfolio):
        """Circuit breaker in RED blocks new buys."""
        cb = CircuitBreakerService()
        cb.evaluate(current_drawdown_pct=Decimal("0.10"))
        assert cb.state == CircuitBreakerState.RED
        assert not cb.allows_new_entries()

    def test_costs_are_realistic(self, ticker, portfolio):
        """Total costs (slippage + txn) are within reasonable bounds."""
        engine = PortfolioEngine(portfolio)
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        fill = engine.process_buy(order, fill_price=Decimal("1000"))

        total_costs = fill.slippage_cost + fill.transaction_cost
        gross = fill.gross_value
        cost_pct = total_costs / gross * 100
        assert cost_pct < Decimal("2")

    def test_net_pnl_includes_all_costs(self, ticker, portfolio):
        """After roundtrip, net PnL accounts for slippage + txn + tax."""
        engine = PortfolioEngine(portfolio)

        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        engine.process_buy(order, fill_price=Decimal("1000"))

        pos = portfolio.open_positions[0]
        engine.process_sell(pos, sell_price=Decimal("1000"))

        assert pos.net_pnl < 0

    def test_multiple_positions(self, ticker, portfolio):
        """Multiple positions tracked independently."""
        engine = PortfolioEngine(portfolio)
        tickers = [
            Ticker(symbol=f"STOCK{i}", exchange=Exchange.NSE, market=Market.INDIA)
            for i in range(3)
        ]
        for t in tickers:
            order = Order(ticker=t, side=OrderSide.BUY, quantity=50)
            engine.process_buy(order, fill_price=Decimal("200"))

        assert len(portfolio.open_positions) == 3
        assert portfolio.invested_value > 0
