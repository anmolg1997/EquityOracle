"""Tests for DrawdownState tracking."""

from decimal import Decimal

from app.domain.risk.models import DrawdownState


class TestDrawdownState:
    def test_initial_state(self):
        dd = DrawdownState()
        assert dd.drawdown_pct == Decimal(0)

    def test_new_peak_updates(self):
        dd = DrawdownState()
        dd.update(Decimal("100"))
        assert dd.peak_value == Decimal("100")
        dd.update(Decimal("120"))
        assert dd.peak_value == Decimal("120")

    def test_drawdown_computed(self):
        dd = DrawdownState()
        dd.update(Decimal("100"))
        dd.update(Decimal("90"))
        assert dd.drawdown_pct == Decimal("10")

    def test_no_drawdown_at_peak(self):
        dd = DrawdownState()
        dd.update(Decimal("100"))
        dd.update(Decimal("110"))
        assert dd.drawdown_pct == Decimal(0)

    def test_recovery_after_drawdown(self):
        dd = DrawdownState()
        dd.update(Decimal("100"))
        dd.update(Decimal("80"))
        assert dd.drawdown_pct == Decimal("20")
        dd.update(Decimal("100"))
        assert dd.drawdown_pct == Decimal(0)
