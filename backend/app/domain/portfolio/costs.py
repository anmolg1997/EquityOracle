"""Realistic cost models — Transaction costs, slippage, and tax.

India-specific defaults, configurable per market via YAML.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.types import OrderSide


@dataclass
class TransactionCostModel:
    """India NSE default costs. All values are proportional unless noted."""

    brokerage_pct: Decimal = Decimal("0.0003")
    stt_buy_pct: Decimal = Decimal("0.001")
    stt_sell_pct: Decimal = Decimal("0.001")
    exchange_txn_pct: Decimal = Decimal("0.0000345")
    gst_on_brokerage_pct: Decimal = Decimal("0.18")
    stamp_duty_buy_pct: Decimal = Decimal("0.00015")
    sebi_fee_pct: Decimal = Decimal("0.000001")

    def total_cost(self, side: OrderSide, value: Decimal) -> Decimal:
        brokerage = value * self.brokerage_pct
        gst = brokerage * self.gst_on_brokerage_pct
        exchange = value * self.exchange_txn_pct
        sebi = value * self.sebi_fee_pct

        if side == OrderSide.BUY:
            stt = value * self.stt_buy_pct
            stamp = value * self.stamp_duty_buy_pct
        else:
            stt = value * self.stt_sell_pct
            stamp = Decimal(0)

        total = brokerage + gst + stt + exchange + stamp + sebi
        return total.quantize(Decimal("0.01"))

    def breakdown(self, side: OrderSide, value: Decimal) -> dict[str, Decimal]:
        brokerage = value * self.brokerage_pct
        return {
            "brokerage": brokerage.quantize(Decimal("0.01")),
            "gst": (brokerage * self.gst_on_brokerage_pct).quantize(Decimal("0.01")),
            "stt": (value * (self.stt_buy_pct if side == OrderSide.BUY else self.stt_sell_pct)).quantize(Decimal("0.01")),
            "exchange_txn": (value * self.exchange_txn_pct).quantize(Decimal("0.01")),
            "stamp_duty": (value * self.stamp_duty_buy_pct if side == OrderSide.BUY else Decimal(0)).quantize(Decimal("0.01")),
            "sebi_fee": (value * self.sebi_fee_pct).quantize(Decimal("0.01")),
        }


@dataclass
class SlippageModel:
    """Volume-aware slippage model."""

    base_slippage: dict[str, Decimal] | None = None

    def __post_init__(self):
        if self.base_slippage is None:
            self.base_slippage = {
                "large": Decimal("0.0005"),
                "mid": Decimal("0.001"),
                "small": Decimal("0.002"),
                "micro": Decimal("0.005"),
            }

    def estimate(
        self,
        order_value: Decimal,
        avg_daily_volume_value: Decimal,
        market_cap_category: str = "mid",
    ) -> Decimal:
        base = self.base_slippage.get(market_cap_category, Decimal("0.002"))

        if avg_daily_volume_value <= 0:
            return order_value * Decimal("0.01")

        participation = order_value / avg_daily_volume_value
        impact_multiplier = Decimal(1) + participation * participation * 100
        slippage_pct = base * impact_multiplier

        return (order_value * slippage_pct).quantize(Decimal("0.01"))


@dataclass
class TaxModel:
    """Indian capital gains tax model."""

    ltcg_rate: Decimal = Decimal("0.125")
    ltcg_exemption: Decimal = Decimal("125000")
    ltcg_holding_months: int = 12
    stcg_rate: Decimal = Decimal("0.20")

    def compute_tax(self, gain: Decimal, hold_days: int) -> Decimal:
        if gain <= 0:
            return Decimal(0)

        if hold_days >= self.ltcg_holding_months * 30:
            taxable = max(gain - self.ltcg_exemption, Decimal(0))
            return (taxable * self.ltcg_rate).quantize(Decimal("0.01"))
        else:
            return (gain * self.stcg_rate).quantize(Decimal("0.01"))
