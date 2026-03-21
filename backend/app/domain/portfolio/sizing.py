"""Position sizing strategies — EqualWeight, ConvictionWeighted, RiskParity, Kelly."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum


class SizingStrategy(str, Enum):
    EQUAL_WEIGHT = "equal_weight"
    CONVICTION_WEIGHTED = "conviction_weighted"
    RISK_PARITY = "risk_parity"
    KELLY = "kelly"


def compute_position_size(
    strategy: SizingStrategy,
    portfolio_value: Decimal,
    max_position_pct: Decimal = Decimal("0.10"),
    confidence: Decimal = Decimal("0.5"),
    volatility: Decimal = Decimal("0.02"),
    win_rate: Decimal = Decimal("0.55"),
    avg_win_loss_ratio: Decimal = Decimal("1.5"),
    n_positions: int = 10,
    liquidity_cap: Decimal | None = None,
) -> Decimal:
    """Compute the dollar value of a position based on strategy."""
    match strategy:
        case SizingStrategy.EQUAL_WEIGHT:
            size = portfolio_value * max_position_pct

        case SizingStrategy.CONVICTION_WEIGHTED:
            # Scale position size with confidence (0.5-1.0 maps to 50%-100% of max)
            scale = Decimal("0.5") + (confidence * Decimal("0.5"))
            size = portfolio_value * max_position_pct * scale

        case SizingStrategy.RISK_PARITY:
            # Target equal risk contribution: lower vol = larger position
            if volatility > 0:
                target_risk = Decimal("0.02")
                size = portfolio_value * target_risk / volatility
            else:
                size = portfolio_value * max_position_pct

        case SizingStrategy.KELLY:
            # Kelly fraction: f = (p * b - q) / b
            p = win_rate
            q = Decimal(1) - p
            b = avg_win_loss_ratio
            if b > 0:
                kelly_fraction = (p * b - q) / b
                # Half-Kelly for safety
                kelly_fraction = max(Decimal(0), kelly_fraction) / 2
                size = portfolio_value * min(kelly_fraction, max_position_pct)
            else:
                size = Decimal(0)

        case _:
            size = portfolio_value * max_position_pct

    # Apply max position cap
    size = min(size, portfolio_value * max_position_pct)

    # Apply liquidity cap
    if liquidity_cap is not None:
        size = min(size, liquidity_cap)

    return size.quantize(Decimal("0.01"))
