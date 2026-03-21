"""Tests for risk manager — pre-trade validation."""

from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, OrderSide, Ticker
from app.domain.portfolio.models import Order, Portfolio, Position
from app.domain.risk.manager import RiskManager


@pytest.fixture
def ticker():
    return Ticker(symbol="INFY", exchange=Exchange.NSE, market=Market.INDIA)


@pytest.fixture
def portfolio(ticker):
    return Portfolio(portfolio_id="test", cash=Decimal("1_000_000"))


@pytest.fixture
def risk_mgr():
    return RiskManager(max_positions=5, max_position_pct=Decimal("0.10"))


class TestRiskValidation:
    def test_valid_order_approved(self, risk_mgr, ticker, portfolio):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("50_000"), portfolio)
        assert result.approved
        assert len(result.reasons) == 0

    def test_max_positions_reached(self, risk_mgr, ticker, portfolio):
        other_ticker = Ticker(symbol="OTHER", exchange=Exchange.NSE, market=Market.INDIA)
        from datetime import date
        for i in range(5):
            t = Ticker(symbol=f"STOCK{i}", exchange=Exchange.NSE, market=Market.INDIA)
            portfolio.positions.append(
                Position(ticker=t, quantity=10, entry_price=Decimal("100"), entry_date=date.today())
            )

        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("50_000"), portfolio)
        assert not result.approved
        assert any("Max positions" in r for r in result.reasons)

    def test_position_size_exceeded(self, risk_mgr, ticker, portfolio):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("200_000"), portfolio)
        assert not result.approved
        assert any("Position size" in r for r in result.reasons)

    def test_duplicate_holding_rejected(self, risk_mgr, ticker, portfolio):
        from datetime import date
        portfolio.positions.append(
            Position(ticker=ticker, quantity=50, entry_price=Decimal("100"), entry_date=date.today())
        )

        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("50_000"), portfolio)
        assert not result.approved
        assert any("Already holding" in r for r in result.reasons)

    def test_insufficient_cash(self, risk_mgr, ticker):
        portfolio = Portfolio(portfolio_id="test", cash=Decimal("10_000"))
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("50_000"), portfolio)
        assert not result.approved
        assert any("Insufficient cash" in r for r in result.reasons)

    def test_multiple_violations_all_reported(self, risk_mgr, ticker):
        portfolio = Portfolio(portfolio_id="test", cash=Decimal("10_000"))
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        result = risk_mgr.validate_order(order, Decimal("200_000"), portfolio)
        assert not result.approved
        assert len(result.reasons) >= 2
