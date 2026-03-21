"""Tests for signal decorrelation — pillar independence checks."""

from decimal import Decimal

from app.domain.analysis.decorrelation import compute_decorrelation


class TestDecorrelation:
    def test_independent_pillars(self):
        result = compute_decorrelation({
            "technical": [90, 10, 50, 70, 30, 80, 20, 60, 40, 55],
            "fundamental": [30, 80, 20, 60, 90, 10, 50, 70, 40, 45],
            "value": [50, 60, 70, 20, 40, 30, 80, 10, 90, 55],
        })
        assert result.effective_signal_count >= Decimal("2.5")
        assert all(v == 1.0 for v in result.adjustments.values())

    def test_correlated_pillars_detected(self):
        base = list(range(1, 101))
        result = compute_decorrelation({
            "pillar_a": base,
            "pillar_b": base,  # perfectly correlated
            "pillar_c": list(reversed(base)),
        })
        assert result.effective_signal_count < Decimal("3")
        assert result.adjustments.get("pillar_b", 1.0) == 0.5

    def test_single_pillar(self):
        result = compute_decorrelation({"only": [1, 2, 3, 4, 5]})
        assert result.effective_signal_count == Decimal("1")

    def test_empty_input(self):
        result = compute_decorrelation({})
        assert result.effective_signal_count == Decimal("0")
