"""Exit signal generation — trailing stop, ATR exit, thesis invalidation."""

from __future__ import annotations

from decimal import Decimal

from app.domain.recommendation.models import ExitRule, ExitType


def generate_exit_rules(
    entry_price: Decimal,
    atr: Decimal | None = None,
    atr_multiplier: Decimal = Decimal("2.5"),
    trailing_stop_pct: Decimal = Decimal("7"),
) -> list[ExitRule]:
    """Generate a set of exit rules for a position."""
    rules: list[ExitRule] = []

    # Trailing stop-loss
    stop_price = entry_price * (1 - trailing_stop_pct / 100)
    rules.append(ExitRule(
        exit_type=ExitType.TRAILING_STOP,
        trigger_value=stop_price,
        description=f"Trailing stop at {trailing_stop_pct}% below entry ({stop_price:.2f})",
    ))

    # ATR-based exit
    if atr and atr > 0:
        atr_stop = entry_price - (atr * atr_multiplier)
        rules.append(ExitRule(
            exit_type=ExitType.ATR_EXIT,
            trigger_value=atr_multiplier,
            description=f"ATR stop at {atr_multiplier}x ATR below entry ({atr_stop:.2f})",
        ))

    # Time-based exit
    rules.append(ExitRule(
        exit_type=ExitType.TIME_EXPIRY,
        trigger_value=Decimal(0),
        description="Exit at horizon expiry if no other trigger fires",
    ))

    return rules


def check_technical_reversal(
    rsi: Decimal | None,
    macd_histogram: Decimal | None,
    volume_ratio: Decimal | None,
) -> bool:
    """Detect a technical reversal: RSI overbought + MACD cross + volume divergence."""
    if rsi is None or macd_histogram is None:
        return False

    rsi_overbought = rsi > Decimal(75)
    macd_bearish = macd_histogram < 0
    volume_weak = volume_ratio is not None and volume_ratio < Decimal("0.8")

    conditions_met = sum([rsi_overbought, macd_bearish, volume_weak])
    return conditions_met >= 2
