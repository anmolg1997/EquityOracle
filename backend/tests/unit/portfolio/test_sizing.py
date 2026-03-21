"""Tests for position sizing strategies."""

from decimal import Decimal

from app.domain.portfolio.sizing import SizingStrategy, compute_position_size


class TestEqualWeight:
    def test_basic_equal_weight(self):
        size = compute_position_size(
            strategy=SizingStrategy.EQUAL_WEIGHT,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.10"),
        )
        assert size == Decimal("100_000.00")

    def test_respects_max_position(self):
        size = compute_position_size(
            strategy=SizingStrategy.EQUAL_WEIGHT,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.05"),
        )
        assert size == Decimal("50_000.00")


class TestConvictionWeighted:
    def test_high_confidence_larger_position(self):
        high = compute_position_size(
            strategy=SizingStrategy.CONVICTION_WEIGHTED,
            portfolio_value=Decimal("1_000_000"),
            confidence=Decimal("0.9"),
        )
        low = compute_position_size(
            strategy=SizingStrategy.CONVICTION_WEIGHTED,
            portfolio_value=Decimal("1_000_000"),
            confidence=Decimal("0.3"),
        )
        assert high > low

    def test_max_confidence_gets_full_position(self):
        size = compute_position_size(
            strategy=SizingStrategy.CONVICTION_WEIGHTED,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.10"),
            confidence=Decimal("1.0"),
        )
        assert size == Decimal("100_000.00")


class TestRiskParity:
    def test_low_vol_gets_larger_position(self):
        low_vol = compute_position_size(
            strategy=SizingStrategy.RISK_PARITY,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.50"),
            volatility=Decimal("0.01"),
        )
        high_vol = compute_position_size(
            strategy=SizingStrategy.RISK_PARITY,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.50"),
            volatility=Decimal("0.05"),
        )
        assert low_vol > high_vol

    def test_zero_vol_falls_back(self):
        size = compute_position_size(
            strategy=SizingStrategy.RISK_PARITY,
            portfolio_value=Decimal("1_000_000"),
            volatility=Decimal("0"),
            max_position_pct=Decimal("0.10"),
        )
        assert size == Decimal("100_000.00")


class TestKelly:
    def test_positive_edge(self):
        size = compute_position_size(
            strategy=SizingStrategy.KELLY,
            portfolio_value=Decimal("1_000_000"),
            win_rate=Decimal("0.60"),
            avg_win_loss_ratio=Decimal("2.0"),
        )
        assert size > 0

    def test_no_edge_zero_position(self):
        size = compute_position_size(
            strategy=SizingStrategy.KELLY,
            portfolio_value=Decimal("1_000_000"),
            win_rate=Decimal("0.30"),
            avg_win_loss_ratio=Decimal("1.0"),
        )
        assert size == Decimal("0.00")

    def test_capped_at_max_position(self):
        size = compute_position_size(
            strategy=SizingStrategy.KELLY,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.05"),
            win_rate=Decimal("0.90"),
            avg_win_loss_ratio=Decimal("5.0"),
        )
        assert size <= Decimal("50_000.00")


class TestLiquidityCap:
    def test_liquidity_cap_applied(self):
        size = compute_position_size(
            strategy=SizingStrategy.EQUAL_WEIGHT,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.10"),
            liquidity_cap=Decimal("50_000"),
        )
        assert size == Decimal("50_000.00")

    def test_no_cap_when_liquidity_is_higher(self):
        size = compute_position_size(
            strategy=SizingStrategy.EQUAL_WEIGHT,
            portfolio_value=Decimal("1_000_000"),
            max_position_pct=Decimal("0.10"),
            liquidity_cap=Decimal("200_000"),
        )
        assert size == Decimal("100_000.00")
