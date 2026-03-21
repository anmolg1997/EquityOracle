"""Shadow A/B testing — parallel weight comparison with statistical significance gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class ShadowPortfolioResult:
    live_return_pct: float
    shadow_return_pct: float
    delta: float
    is_significant: bool
    p_value: float
    duration_days: int
    recommendation: str


@dataclass
class ShadowPortfolio:
    """Tracks a shadow portfolio with proposed new weights."""

    weights: dict[str, float]
    daily_returns: list[float] = field(default_factory=list)
    start_date: str = ""


class ABTestingService:
    """Runs shadow portfolios to validate weight changes before deployment.

    When proposing new weights, run them in parallel as a shadow portfolio
    for 2 weeks. Only switch if shadow outperforms with statistical
    significance (p < 0.1).
    """

    SIGNIFICANCE_THRESHOLD = 0.10
    MIN_DURATION_DAYS = 14

    def __init__(self) -> None:
        self._shadow: ShadowPortfolio | None = None
        self._live_returns: list[float] = []

    def start_test(self, proposed_weights: dict[str, float]) -> None:
        self._shadow = ShadowPortfolio(weights=proposed_weights)
        self._live_returns = []
        log.info("ab_test_started", weights=proposed_weights)

    def record_daily(self, live_return: float, shadow_return: float) -> None:
        if self._shadow is None:
            return
        self._live_returns.append(live_return)
        self._shadow.daily_returns.append(shadow_return)

    def evaluate(self) -> ShadowPortfolioResult | None:
        if self._shadow is None or len(self._shadow.daily_returns) < self.MIN_DURATION_DAYS:
            return None

        live_arr = np.array(self._live_returns)
        shadow_arr = np.array(self._shadow.daily_returns)

        delta = float(np.mean(shadow_arr) - np.mean(live_arr))
        duration = len(self._shadow.daily_returns)

        # Two-sample t-test
        from scipy.stats import ttest_ind
        t_stat, p_value = ttest_ind(shadow_arr, live_arr)
        p_value = float(p_value)

        is_sig = p_value < self.SIGNIFICANCE_THRESHOLD and delta > 0

        recommendation = "adopt" if is_sig else "reject"
        if duration < self.MIN_DURATION_DAYS:
            recommendation = "continue_testing"

        result = ShadowPortfolioResult(
            live_return_pct=float(np.sum(live_arr) * 100),
            shadow_return_pct=float(np.sum(shadow_arr) * 100),
            delta=round(delta * 100, 4),
            is_significant=is_sig,
            p_value=round(p_value, 4),
            duration_days=duration,
            recommendation=recommendation,
        )

        if is_sig:
            log.info("ab_test_significant", delta=result.delta, p=result.p_value)
        else:
            log.info("ab_test_not_significant", delta=result.delta, p=result.p_value)

        return result

    def reset(self) -> None:
        self._shadow = None
        self._live_returns = []
