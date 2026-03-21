"""Circuit breaker — Amber/Red/Black levels with auto-pause and immutable audit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.core.logging import get_logger
from app.core.types import CircuitBreakerState
from app.domain.risk.models import CircuitBreakerLog

log = get_logger(__name__)


@dataclass
class CircuitBreakerConfig:
    amber_accuracy_threshold: Decimal = Decimal("0.40")
    amber_window_days: int = 5
    red_accuracy_threshold: Decimal = Decimal("0.35")
    red_window_days: int = 10
    red_drawdown_threshold: Decimal = Decimal("0.08")
    black_drawdown_threshold: Decimal = Decimal("0.15")


class CircuitBreakerService:
    """Monitors system performance and enforces defensive actions.

    State transitions are immutable-logged:
    GREEN -> AMBER: reduce position sizes by 50%, alert
    AMBER -> RED: pause new entries, exits only, escalate
    RED -> BLACK: flatten to cash, full stop, require manual restart
    Any -> GREEN: only via manual reset or conditions recovery
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState.GREEN
        self._audit_log: list[CircuitBreakerLog] = []

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def audit_log(self) -> list[CircuitBreakerLog]:
        return list(self._audit_log)

    def evaluate(
        self,
        rolling_accuracy_5d: Decimal | None = None,
        rolling_accuracy_10d: Decimal | None = None,
        current_drawdown_pct: Decimal = Decimal(0),
    ) -> CircuitBreakerState:
        """Evaluate metrics and potentially transition state."""
        previous = self._state

        # BLACK: maximum drawdown
        if current_drawdown_pct >= self._config.black_drawdown_threshold:
            self._transition(CircuitBreakerState.BLACK, f"Drawdown {current_drawdown_pct:.1%} >= {self._config.black_drawdown_threshold:.1%}")
            return self._state

        # RED: accuracy crisis or significant drawdown
        if rolling_accuracy_10d is not None and rolling_accuracy_10d < self._config.red_accuracy_threshold:
            self._transition(CircuitBreakerState.RED, f"10d accuracy {rolling_accuracy_10d:.1%} < {self._config.red_accuracy_threshold:.1%}")
            return self._state

        if current_drawdown_pct >= self._config.red_drawdown_threshold:
            self._transition(CircuitBreakerState.RED, f"Drawdown {current_drawdown_pct:.1%} >= {self._config.red_drawdown_threshold:.1%}")
            return self._state

        # AMBER: early warning
        if rolling_accuracy_5d is not None and rolling_accuracy_5d < self._config.amber_accuracy_threshold:
            self._transition(CircuitBreakerState.AMBER, f"5d accuracy {rolling_accuracy_5d:.1%} < {self._config.amber_accuracy_threshold:.1%}")
            return self._state

        # Recovery to GREEN
        if self._state != CircuitBreakerState.BLACK:
            if self._state != CircuitBreakerState.GREEN:
                self._transition(CircuitBreakerState.GREEN, "Metrics recovered to normal range")

        return self._state

    def manual_reset(self) -> None:
        """Manual reset from any state to GREEN."""
        self._transition(CircuitBreakerState.GREEN, "Manual reset by operator")

    def allows_new_entries(self) -> bool:
        return self._state in (CircuitBreakerState.GREEN, CircuitBreakerState.AMBER)

    def position_size_multiplier(self) -> Decimal:
        match self._state:
            case CircuitBreakerState.GREEN:
                return Decimal(1)
            case CircuitBreakerState.AMBER:
                return Decimal("0.5")
            case _:
                return Decimal(0)

    def _transition(self, new_state: CircuitBreakerState, reason: str) -> None:
        if new_state == self._state:
            return

        entry = CircuitBreakerLog(
            previous_state=self._state,
            new_state=new_state,
            trigger_reason=reason,
        )
        self._audit_log.append(entry)

        log.warning(
            "circuit_breaker_transition",
            from_state=self._state.value,
            to_state=new_state.value,
            reason=reason,
        )
        self._state = new_state
