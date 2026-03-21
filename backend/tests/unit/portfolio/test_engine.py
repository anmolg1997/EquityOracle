"""Tests for portfolio engine — buy/sell with realistic costs."""

from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, OrderSide, Ticker
from app.domain.portfolio.engine import PortfolioEngine
from app.domain.portfolio.models import Order, Portfolio, Position


@pytest.fixture
def ticker():
    return Ticker(symbol="RELIANCE", exchange=Exchange.NSE, market=Market.INDIA)


@pytest.fixture
def portfolio():
    return Portfolio(portfolio_id="test", cash=Decimal("1_000_000"))


@pytest.fixture
def engine(portfolio):
    return PortfolioEngine(portfolio=portfolio)


class TestBuyProcessing:
    def test_successful_buy(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        fill = engine.process_buy(order, fill_price=Decimal("2500"))

        assert fill.fill_quantity == 100
        assert fill.gross_value == Decimal("250_000")
        assert fill.slippage_cost > 0
        assert fill.transaction_cost > 0
        assert fill.net_value > fill.gross_value

    def test_cash_deducted_after_buy(self, engine, ticker):
        initial_cash = engine.portfolio.cash
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=10)
        fill = engine.process_buy(order, fill_price=Decimal("100"))

        assert engine.portfolio.cash < initial_cash
        assert engine.portfolio.cash == initial_cash - fill.net_value

    def test_position_created_after_buy(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=50)
        engine.process_buy(order, fill_price=Decimal("1000"))

        assert len(engine.portfolio.open_positions) == 1
        pos = engine.portfolio.open_positions[0]
        assert pos.ticker == ticker
        assert pos.quantity == 50

    def test_insufficient_cash_raises(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=10000)
        with pytest.raises(ValueError, match="Insufficient cash"):
            engine.process_buy(order, fill_price=Decimal("200"))

    def test_slippage_increases_effective_price(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        fill = engine.process_buy(order, fill_price=Decimal("1000"))
        assert fill.fill_price > Decimal("1000")


class TestSellProcessing:
    def test_successful_sell(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        engine.process_buy(order, fill_price=Decimal("100"))

        position = engine.portfolio.open_positions[0]
        fill = engine.process_sell(position, sell_price=Decimal("120"))

        assert fill.fill_quantity == 100
        assert not position.is_open
        assert position.exit_price is not None

    def test_cash_added_after_sell(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        engine.process_buy(order, fill_price=Decimal("100"))

        cash_after_buy = engine.portfolio.cash
        position = engine.portfolio.open_positions[0]
        engine.process_sell(position, sell_price=Decimal("120"))

        assert engine.portfolio.cash > cash_after_buy

    def test_sell_applies_slippage_and_costs(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        engine.process_buy(order, fill_price=Decimal("100"))

        position = engine.portfolio.open_positions[0]
        fill = engine.process_sell(position, sell_price=Decimal("100"))

        assert fill.slippage_cost > 0
        assert fill.transaction_cost > 0
        assert fill.fill_price < Decimal("100")


class TestPriceUpdates:
    def test_update_prices(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        engine.process_buy(order, fill_price=Decimal("100"))

        engine.update_prices({str(ticker): Decimal("120")})
        pos = engine.portfolio.open_positions[0]
        assert pos.current_price == Decimal("120")

    def test_update_unknown_ticker_ignored(self, engine, ticker):
        order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
        engine.process_buy(order, fill_price=Decimal("100"))

        other = Ticker(symbol="OTHER", exchange=Exchange.NSE, market=Market.INDIA)
        engine.update_prices({str(other): Decimal("999")})
        pos = engine.portfolio.open_positions[0]
        assert pos.current_price != Decimal("999")
