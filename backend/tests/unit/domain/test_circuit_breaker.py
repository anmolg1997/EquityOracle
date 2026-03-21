"""Tests for circuit breaker state transitions."""

from decimal import Decimal

from app.core.types import CircuitBreakerState
from app.domain.risk.circuit_breaker import CircuitBreakerService


class TestCircuitBreaker:
    def test_starts_green(self):
        cb = CircuitBreakerService()
        assert cb.state == CircuitBreakerState.GREEN
        assert cb.allows_new_entries()
        assert cb.position_size_multiplier() == Decimal(1)

    def test_amber_on_low_accuracy(self):
        cb = CircuitBreakerService()
        cb.evaluate(rolling_accuracy_5d=Decimal("0.35"))
        assert cb.state == CircuitBreakerState.AMBER
        assert cb.allows_new_entries()
        assert cb.position_size_multiplier() == Decimal("0.5")

    def test_red_on_accuracy_crisis(self):
        cb = CircuitBreakerService()
        cb.evaluate(rolling_accuracy_10d=Decimal("0.30"))
        assert cb.state == CircuitBreakerState.RED
        assert not cb.allows_new_entries()
        assert cb.position_size_multiplier() == Decimal(0)

    def test_red_on_drawdown(self):
        cb = CircuitBreakerService()
        cb.evaluate(current_drawdown_pct=Decimal("0.10"))
        assert cb.state == CircuitBreakerState.RED

    def test_black_on_severe_drawdown(self):
        cb = CircuitBreakerService()
        cb.evaluate(current_drawdown_pct=Decimal("0.20"))
        assert cb.state == CircuitBreakerState.BLACK
        assert not cb.allows_new_entries()

    def test_recovery_to_green(self):
        cb = CircuitBreakerService()
        cb.evaluate(rolling_accuracy_5d=Decimal("0.35"))
        assert cb.state == CircuitBreakerState.AMBER

        cb.evaluate(rolling_accuracy_5d=Decimal("0.55"), rolling_accuracy_10d=Decimal("0.50"))
        assert cb.state == CircuitBreakerState.GREEN

    def test_manual_reset(self):
        cb = CircuitBreakerService()
        cb.evaluate(current_drawdown_pct=Decimal("0.20"))
        assert cb.state == CircuitBreakerState.BLACK

        cb.manual_reset()
        assert cb.state == CircuitBreakerState.GREEN

    def test_audit_log(self):
        cb = CircuitBreakerService()
        cb.evaluate(rolling_accuracy_5d=Decimal("0.35"))
        cb.manual_reset()
        assert len(cb.audit_log) == 2
        assert cb.audit_log[0].new_state == CircuitBreakerState.AMBER
        assert cb.audit_log[1].new_state == CircuitBreakerState.GREEN
