"""Tests for autonomy controller — per-engine flags + circuit breaker integration."""

from decimal import Decimal

from app.application.autonomy.controller import AutonomyController
from app.core.types import AutonomyLevel, CircuitBreakerState
from app.domain.risk.circuit_breaker import CircuitBreakerConfig, CircuitBreakerService


class TestAutonomyController:
    def test_scanner_always_auto(self):
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        assert ctrl.can_execute("scanner")

    def test_manual_engine_cannot_execute(self):
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        assert not ctrl.can_execute("paper_trader")

    def test_set_engine_level(self):
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        ctrl.set_engine_level("paper_trader", AutonomyLevel.FULL_AUTO)
        assert ctrl.can_execute("paper_trader")

    def test_black_cb_blocks_all(self):
        cb = CircuitBreakerService()
        cb.evaluate(current_drawdown_pct=Decimal("0.20"))
        assert cb.state == CircuitBreakerState.BLACK

        ctrl = AutonomyController(cb)
        assert not ctrl.can_execute("scanner")
        assert not ctrl.can_execute("recommender")

    def test_red_cb_blocks_trading(self):
        cb = CircuitBreakerService()
        cb.evaluate(current_drawdown_pct=Decimal("0.10"))
        assert cb.state == CircuitBreakerState.RED

        ctrl = AutonomyController(cb)
        assert ctrl.can_execute("scanner")
        assert not ctrl.can_execute("recommender")
        assert not ctrl.can_execute("paper_trader")

    def test_amber_cb_allows_all_non_manual(self):
        cb = CircuitBreakerService()
        cb.evaluate(rolling_accuracy_5d=Decimal("0.35"))
        assert cb.state == CircuitBreakerState.AMBER

        ctrl = AutonomyController(cb)
        assert ctrl.can_execute("scanner")
        assert ctrl.can_execute("recommender")

    def test_unknown_engine_returns_false(self):
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        assert not ctrl.can_execute("nonexistent")

    def test_get_all_configs(self):
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        configs = ctrl.get_all_configs()
        assert "scanner" in configs
        assert configs["scanner"]["circuit_breaker"] == "green"
        assert configs["scanner"]["can_execute"] is True

    def test_get_engine_config(self):
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        config = ctrl.get_engine_config("scanner")
        assert config is not None
        assert config.name == "scanner"
        assert config.level == AutonomyLevel.FULL_AUTO
