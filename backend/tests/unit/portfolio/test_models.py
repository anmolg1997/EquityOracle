"""Tests for portfolio domain models — Position, Portfolio properties."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.types import Exchange, Market, Ticker
from app.domain.portfolio.models import Portfolio, Position


@pytest.fixture
def ticker():
    return Ticker(symbol="TCS", exchange=Exchange.NSE, market=Market.INDIA)


class TestPosition:
    def test_gross_pnl_open_position(self, ticker):
        pos = Position(
            ticker=ticker, quantity=100, entry_price=Decimal("100"),
            entry_date=date(2024, 1, 1), current_price=Decimal("120"),
        )
        assert pos.gross_pnl == Decimal("2000")

    def test_gross_pnl_closed_position(self, ticker):
        pos = Position(
            ticker=ticker, quantity=100, entry_price=Decimal("100"),
            entry_date=date(2024, 1, 1), exit_price=Decimal("110"),
            is_open=False,
        )
        assert pos.gross_pnl == Decimal("1000")

    def test_net_pnl_accounts_for_costs(self, ticker):
        pos = Position(
            ticker=ticker, quantity=100, entry_price=Decimal("100"),
            entry_date=date(2024, 1, 1), current_price=Decimal("120"),
            entry_costs=Decimal("50"), slippage_total=Decimal("30"),
        )
        assert pos.net_pnl == Decimal("2000") - Decimal("50") - Decimal("30")

    def test_gross_return_pct(self, ticker):
        pos = Position(
            ticker=ticker, quantity=100, entry_price=Decimal("100"),
            entry_date=date(2024, 1, 1), current_price=Decimal("110"),
        )
        assert pos.gross_return_pct == Decimal("10")

    def test_hold_days(self, ticker):
        pos = Position(
            ticker=ticker, quantity=100, entry_price=Decimal("100"),
            entry_date=date(2024, 1, 1), exit_date=date(2024, 2, 1),
            is_open=False,
        )
        assert pos.hold_days == 31


class TestPortfolio:
    def test_total_value(self, ticker):
        portfolio = Portfolio(
            portfolio_id="test", cash=Decimal("500_000"),
            positions=[
                Position(
                    ticker=ticker, quantity=100, entry_price=Decimal("1000"),
                    entry_date=date(2024, 1, 1), current_price=Decimal("1200"),
                )
            ],
        )
        assert portfolio.total_value == Decimal("500_000") + Decimal("120_000")

    def test_open_vs_closed_positions(self, ticker):
        portfolio = Portfolio(
            portfolio_id="test",
            positions=[
                Position(
                    ticker=ticker, quantity=100, entry_price=Decimal("100"),
                    entry_date=date(2024, 1, 1), is_open=True,
                ),
                Position(
                    ticker=ticker, quantity=50, entry_price=Decimal("200"),
                    entry_date=date(2024, 1, 1), is_open=False,
                ),
            ],
        )
        assert len(portfolio.open_positions) == 1
        assert len(portfolio.closed_positions) == 1

    def test_total_return_pct(self, ticker):
        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("1_100_000"),
            initial_capital=Decimal("1_000_000"),
        )
        assert portfolio.total_return_pct == Decimal("10")

    def test_gross_pnl_aggregate(self, ticker):
        portfolio = Portfolio(
            portfolio_id="test",
            positions=[
                Position(
                    ticker=ticker, quantity=100, entry_price=Decimal("100"),
                    entry_date=date(2024, 1, 1), current_price=Decimal("120"),
                ),
                Position(
                    ticker=ticker, quantity=50, entry_price=Decimal("200"),
                    entry_date=date(2024, 1, 1), current_price=Decimal("180"),
                ),
            ],
        )
        assert portfolio.gross_pnl == Decimal("2000") + Decimal("-1000")
