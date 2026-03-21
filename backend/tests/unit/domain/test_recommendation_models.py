"""Tests for recommendation domain models — ExitRule triggering, Thesis, Debate."""

from datetime import date, datetime
from decimal import Decimal

from app.core.types import Exchange, Market, Ticker, TimeHorizon
from app.domain.recommendation.models import (
    DecisionAudit,
    DebateResult,
    ExitRule,
    ExitType,
    Recommendation,
    Signal,
    SignalDirection,
    Thesis,
)


class TestExitRuleTrigger:
    def test_trailing_stop_triggered_below(self):
        rule = ExitRule(exit_type=ExitType.TRAILING_STOP, trigger_value=Decimal("90"))
        assert rule.is_triggered(Decimal("85"), Decimal("100"))

    def test_trailing_stop_not_triggered_above(self):
        rule = ExitRule(exit_type=ExitType.TRAILING_STOP, trigger_value=Decimal("90"))
        assert not rule.is_triggered(Decimal("95"), Decimal("100"))

    def test_atr_exit_triggered(self):
        rule = ExitRule(exit_type=ExitType.ATR_EXIT, trigger_value=Decimal("2"))
        assert rule.is_triggered(Decimal("88"), Decimal("100"), atr=Decimal("5"))

    def test_atr_exit_not_triggered(self):
        rule = ExitRule(exit_type=ExitType.ATR_EXIT, trigger_value=Decimal("2"))
        assert not rule.is_triggered(Decimal("95"), Decimal("100"), atr=Decimal("5"))

    def test_atr_exit_no_atr_returns_false(self):
        rule = ExitRule(exit_type=ExitType.ATR_EXIT, trigger_value=Decimal("2"))
        assert not rule.is_triggered(Decimal("85"), Decimal("100"))

    def test_time_expiry_never_triggers(self):
        rule = ExitRule(exit_type=ExitType.TIME_EXPIRY, trigger_value=Decimal("0"))
        assert not rule.is_triggered(Decimal("50"), Decimal("100"))


class TestDecisionAudit:
    def test_full_audit_record(self):
        ticker = Ticker(symbol="TCS", exchange=Exchange.NSE, market=Market.INDIA)
        audit = DecisionAudit(
            correlation_id="test-123",
            ticker=ticker,
            horizon=TimeHorizon.WEEK_1,
            decision=SignalDirection.BUY,
            technical_score=Decimal("75"),
            factor_score=Decimal("70"),
            composite_score=Decimal("72"),
            confidence=Decimal("0.75"),
            risk_check_passed=True,
        )
        assert audit.ticker == ticker
        assert audit.decision == SignalDirection.BUY
        assert audit.risk_check_passed


class TestRecommendationModel:
    def test_recommendation_with_signal(self):
        ticker = Ticker(symbol="INFY", exchange=Exchange.NSE, market=Market.INDIA)
        signal = Signal(
            ticker=ticker, direction=SignalDirection.BUY,
            horizon=TimeHorizon.MONTH_1,
            strength=Decimal("80"), expected_return_pct=Decimal("12"),
            confidence=Decimal("0.8"),
        )
        rec = Recommendation(signal=signal)
        assert rec.actual_return_pct is None
        assert rec.is_accurate is None

    def test_recommendation_with_exit_rules(self):
        ticker = Ticker(symbol="INFY", exchange=Exchange.NSE, market=Market.INDIA)
        signal = Signal(
            ticker=ticker, direction=SignalDirection.BUY,
            horizon=TimeHorizon.WEEK_1,
            strength=Decimal("70"), expected_return_pct=Decimal("5"),
            confidence=Decimal("0.7"),
        )
        exit_rules = [
            ExitRule(exit_type=ExitType.TRAILING_STOP, trigger_value=Decimal("93")),
            ExitRule(exit_type=ExitType.TIME_EXPIRY, trigger_value=Decimal("0")),
        ]
        rec = Recommendation(signal=signal, exit_rules=exit_rules)
        assert len(rec.exit_rules) == 2


class TestDebateResult:
    def test_default_verdict_is_hold(self):
        ticker = Ticker(symbol="TCS", exchange=Exchange.NSE, market=Market.INDIA)
        debate = DebateResult(ticker=ticker)
        assert debate.verdict == SignalDirection.HOLD
