"""Tests for transaction cost, slippage, and tax models."""

from decimal import Decimal

from app.core.types import OrderSide
from app.domain.portfolio.costs import SlippageModel, TaxModel, TransactionCostModel


class TestTransactionCosts:
    def test_buy_costs_india(self):
        model = TransactionCostModel()
        cost = model.total_cost(OrderSide.BUY, Decimal("1_000_000"))
        assert cost > 0
        assert cost < Decimal("5000")  # ~0.5% max

    def test_sell_costs_india(self):
        model = TransactionCostModel()
        cost = model.total_cost(OrderSide.SELL, Decimal("1_000_000"))
        assert cost > 0

    def test_cost_breakdown(self):
        model = TransactionCostModel()
        breakdown = model.breakdown(OrderSide.BUY, Decimal("1_000_000"))
        assert "brokerage" in breakdown
        assert "stt" in breakdown
        assert "gst" in breakdown
        total = sum(breakdown.values())
        assert total == model.total_cost(OrderSide.BUY, Decimal("1_000_000"))


class TestSlippage:
    def test_large_cap_low_slippage(self):
        model = SlippageModel()
        slippage = model.estimate(Decimal("100_000"), Decimal("1_000_000_000"), "large")
        assert slippage < Decimal("100")

    def test_micro_cap_higher_slippage(self):
        model = SlippageModel()
        slippage = model.estimate(Decimal("100_000"), Decimal("500_000"), "micro")
        assert slippage > Decimal("100")


class TestTax:
    def test_stcg_india(self):
        model = TaxModel()
        tax = model.compute_tax(Decimal("100_000"), hold_days=100)
        assert tax == Decimal("20000.00")

    def test_ltcg_india_below_exemption(self):
        model = TaxModel()
        tax = model.compute_tax(Decimal("100_000"), hold_days=400)
        assert tax == Decimal("0.00")

    def test_ltcg_india_above_exemption(self):
        model = TaxModel()
        tax = model.compute_tax(Decimal("500_000"), hold_days=400)
        expected = (Decimal("500_000") - Decimal("125_000")) * Decimal("0.125")
        assert tax == expected.quantize(Decimal("0.01"))

    def test_loss_no_tax(self):
        model = TaxModel()
        tax = model.compute_tax(Decimal("-50_000"), hold_days=100)
        assert tax == Decimal("0")
