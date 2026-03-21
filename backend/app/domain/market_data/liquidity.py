"""Liquidity scoring, minimum volume filtering, and market impact estimation.

Pure domain logic — no external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.types import Ticker
from app.domain.market_data.models import LiquidityProfile, OHLCV


def compute_liquidity_profile(
    ticker: Ticker,
    ohlcv_history: list[OHLCV],
    lookback_days: int = 20,
) -> LiquidityProfile:
    """Compute a liquidity profile from recent OHLCV data."""
    if not ohlcv_history:
        return LiquidityProfile(ticker=ticker)

    recent = sorted(ohlcv_history, key=lambda r: r.date, reverse=True)[:lookback_days]
    recent = [r for r in recent if r.volume > 0]

    if not recent:
        return LiquidityProfile(ticker=ticker)

    avg_volume = sum(r.volume for r in recent) // len(recent)
    avg_value = sum(r.daily_value for r in recent) / len(recent)

    if avg_value >= Decimal("500_000_000"):
        category = "large"
    elif avg_value >= Decimal("50_000_000"):
        category = "mid"
    elif avg_value >= Decimal("5_000_000"):
        category = "small"
    else:
        category = "micro"

    score = _compute_score(avg_value)

    return LiquidityProfile(
        ticker=ticker,
        avg_daily_volume_20d=avg_volume,
        avg_daily_value_20d=avg_value,
        market_cap_category=category,
        liquidity_score=score,
    )


def _compute_score(avg_daily_value: Decimal) -> Decimal:
    """0-100 score based on average daily traded value."""
    if avg_daily_value <= 0:
        return Decimal(0)

    thresholds = [
        (Decimal("1_000_000_000"), Decimal(100)),
        (Decimal("500_000_000"), Decimal(90)),
        (Decimal("100_000_000"), Decimal(75)),
        (Decimal("50_000_000"), Decimal(60)),
        (Decimal("10_000_000"), Decimal(40)),
        (Decimal("5_000_000"), Decimal(25)),
        (Decimal("1_000_000"), Decimal(10)),
    ]

    for threshold, score in thresholds:
        if avg_daily_value >= threshold:
            return score
    return Decimal(5)


def passes_liquidity_filter(
    profile: LiquidityProfile,
    min_daily_value: Decimal,
) -> bool:
    return profile.avg_daily_value_20d >= min_daily_value


@dataclass
class ImpactEstimate:
    estimated_slippage_pct: Decimal
    participation_rate: Decimal
    is_feasible: bool
    warning: str = ""


def estimate_market_impact(
    profile: LiquidityProfile,
    order_value: Decimal,
) -> ImpactEstimate:
    """Estimate the market impact (slippage) of a trade based on order size
    relative to average daily volume.

    Uses a non-linear model: impact grows quadratically with participation rate.
    """
    if profile.avg_daily_value_20d <= 0:
        return ImpactEstimate(
            estimated_slippage_pct=Decimal("5.0"),
            participation_rate=Decimal("100"),
            is_feasible=False,
            warning="No liquidity data available",
        )

    participation = order_value / profile.avg_daily_value_20d * 100
    base_slippage = {
        "large": Decimal("0.05"),
        "mid": Decimal("0.10"),
        "small": Decimal("0.25"),
        "micro": Decimal("0.50"),
    }.get(profile.market_cap_category, Decimal("0.50"))

    participation_multiplier = Decimal(1) + (participation / 100) ** 2
    estimated_slippage = base_slippage * participation_multiplier

    is_feasible = participation < Decimal(10)
    warning = ""
    if participation >= Decimal(5):
        warning = f"Order is {participation:.1f}% of daily volume — significant market impact expected"
    elif participation >= Decimal(2):
        warning = f"Order is {participation:.1f}% of daily volume — moderate impact"

    return ImpactEstimate(
        estimated_slippage_pct=round(estimated_slippage, 4),
        participation_rate=round(participation, 2),
        is_feasible=is_feasible,
        warning=warning,
    )


def max_position_by_liquidity(
    profile: LiquidityProfile,
    max_participation_pct: Decimal = Decimal(5),
) -> Decimal:
    """Maximum position value that keeps participation rate below threshold."""
    return profile.avg_daily_value_20d * max_participation_pct / 100
