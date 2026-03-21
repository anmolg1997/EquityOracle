"""Risk manager — pre-trade validation and portfolio monitoring."""

from __future__ import annotations

from decimal import Decimal

from app.core.logging import get_logger
from app.domain.portfolio.models import Order, Portfolio
from app.domain.risk.models import RiskCheckResult

log = get_logger(__name__)


class RiskManager:
    """Validates trades against risk limits before execution."""

    def __init__(
        self,
        max_position_pct: Decimal = Decimal("0.10"),
        max_sector_pct: Decimal = Decimal("0.30"),
        max_positions: int = 25,
        max_drawdown_pct: Decimal = Decimal("0.15"),
    ) -> None:
        self._max_position_pct = max_position_pct
        self._max_sector_pct = max_sector_pct
        self._max_positions = max_positions
        self._max_drawdown_pct = max_drawdown_pct

    def validate_order(
        self,
        order: Order,
        order_value: Decimal,
        portfolio: Portfolio,
    ) -> RiskCheckResult:
        """Run pre-trade risk checks."""
        reasons: list[str] = []

        # Position count limit
        if len(portfolio.open_positions) >= self._max_positions:
            reasons.append(f"Max positions ({self._max_positions}) reached")

        # Position size limit
        if portfolio.total_value > 0:
            position_pct = order_value / portfolio.total_value
            if position_pct > self._max_position_pct:
                reasons.append(
                    f"Position size {position_pct:.1%} exceeds max {self._max_position_pct:.1%}"
                )

        # Duplicate check
        existing = [p for p in portfolio.open_positions if p.ticker == order.ticker]
        if existing:
            reasons.append(f"Already holding {order.ticker}")

        # Cash sufficiency
        if order_value > portfolio.cash:
            reasons.append(f"Insufficient cash: need {order_value}, have {portfolio.cash}")

        return RiskCheckResult(
            approved=len(reasons) == 0,
            reasons=reasons,
        )
