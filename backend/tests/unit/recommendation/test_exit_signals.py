"""Tests for exit signal generation — trailing stop, ATR, reversal detection."""

from decimal import Decimal

from app.domain.recommendation.exit_signals import (
    check_technical_reversal,
    generate_exit_rules,
)
from app.domain.recommendation.models import ExitType


class TestExitRuleGeneration:
    def test_always_generates_trailing_stop(self):
        rules = generate_exit_rules(entry_price=Decimal("100"))
        types = [r.exit_type for r in rules]
        assert ExitType.TRAILING_STOP in types

    def test_always_generates_time_expiry(self):
        rules = generate_exit_rules(entry_price=Decimal("100"))
        types = [r.exit_type for r in rules]
        assert ExitType.TIME_EXPIRY in types

    def test_atr_exit_when_atr_provided(self):
        rules = generate_exit_rules(entry_price=Decimal("100"), atr=Decimal("5"))
        types = [r.exit_type for r in rules]
        assert ExitType.ATR_EXIT in types

    def test_no_atr_exit_without_atr(self):
        rules = generate_exit_rules(entry_price=Decimal("100"))
        types = [r.exit_type for r in rules]
        assert ExitType.ATR_EXIT not in types

    def test_trailing_stop_value(self):
        rules = generate_exit_rules(
            entry_price=Decimal("100"), trailing_stop_pct=Decimal("10"),
        )
        stop_rule = [r for r in rules if r.exit_type == ExitType.TRAILING_STOP][0]
        assert stop_rule.trigger_value == Decimal("90")

    def test_custom_atr_multiplier(self):
        rules = generate_exit_rules(
            entry_price=Decimal("100"), atr=Decimal("5"), atr_multiplier=Decimal("3"),
        )
        atr_rule = [r for r in rules if r.exit_type == ExitType.ATR_EXIT][0]
        assert atr_rule.trigger_value == Decimal("3")


class TestExitRuleTriggering:
    def test_trailing_stop_triggered(self):
        rules = generate_exit_rules(entry_price=Decimal("100"), trailing_stop_pct=Decimal("10"))
        stop = [r for r in rules if r.exit_type == ExitType.TRAILING_STOP][0]
        assert stop.is_triggered(Decimal("85"), Decimal("100"))

    def test_trailing_stop_not_triggered(self):
        rules = generate_exit_rules(entry_price=Decimal("100"), trailing_stop_pct=Decimal("10"))
        stop = [r for r in rules if r.exit_type == ExitType.TRAILING_STOP][0]
        assert not stop.is_triggered(Decimal("95"), Decimal("100"))

    def test_atr_exit_triggered(self):
        rules = generate_exit_rules(
            entry_price=Decimal("100"), atr=Decimal("5"), atr_multiplier=Decimal("2"),
        )
        atr_rule = [r for r in rules if r.exit_type == ExitType.ATR_EXIT][0]
        assert atr_rule.is_triggered(Decimal("88"), Decimal("100"), atr=Decimal("5"))

    def test_atr_exit_not_triggered(self):
        rules = generate_exit_rules(
            entry_price=Decimal("100"), atr=Decimal("5"), atr_multiplier=Decimal("2"),
        )
        atr_rule = [r for r in rules if r.exit_type == ExitType.ATR_EXIT][0]
        assert not atr_rule.is_triggered(Decimal("95"), Decimal("100"), atr=Decimal("5"))


class TestTechnicalReversal:
    def test_reversal_detected(self):
        assert check_technical_reversal(
            rsi=Decimal("80"), macd_histogram=Decimal("-2"), volume_ratio=Decimal("0.5"),
        )

    def test_no_reversal_healthy_indicators(self):
        assert not check_technical_reversal(
            rsi=Decimal("60"), macd_histogram=Decimal("3"), volume_ratio=Decimal("1.5"),
        )

    def test_partial_reversal_not_enough(self):
        assert not check_technical_reversal(
            rsi=Decimal("80"), macd_histogram=Decimal("3"), volume_ratio=Decimal("1.2"),
        )

    def test_none_inputs_no_reversal(self):
        assert not check_technical_reversal(rsi=None, macd_histogram=None, volume_ratio=None)
