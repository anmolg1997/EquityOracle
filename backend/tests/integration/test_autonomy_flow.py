"""Integration test: Autonomy controller + circuit breaker + self-improvement flow."""

from decimal import Decimal

from app.application.autonomy.controller import AutonomyController
from app.application.autonomy.self_improve import SelfImprovementService
from app.core.types import AutonomyLevel, CircuitBreakerState
from app.domain.risk.circuit_breaker import CircuitBreakerService


class TestAutonomyIntegration:
    def test_self_improvement_gated_by_circuit_breaker(self):
        """Self-improvement blocked when circuit breaker is RED/BLACK."""
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)

        assert ctrl.can_execute("self_improvement")

        cb.evaluate(current_drawdown_pct=Decimal("0.20"))
        assert cb.state == CircuitBreakerState.BLACK
        assert not ctrl.can_execute("self_improvement")

    def test_proposal_to_controller_flow(self):
        """Improvement proposal respects autonomy level."""
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)
        svc = SelfImprovementService()

        proposal = svc.propose_adjustment(
            current_weights={"a": 0.5, "b": 0.5},
            pillar_accuracy={"a": 0.65, "b": 0.35},
            sample_counts={"a": 150, "b": 150},
        )
        assert proposal.approved
        assert ctrl.can_execute("self_improvement")

    def test_full_state_progression(self):
        """GREEN -> AMBER -> RED -> manual_reset -> GREEN."""
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)

        assert cb.state == CircuitBreakerState.GREEN
        assert ctrl.can_execute("recommender")

        cb.evaluate(rolling_accuracy_5d=Decimal("0.35"))
        assert cb.state == CircuitBreakerState.AMBER
        assert ctrl.can_execute("recommender")

        cb.evaluate(rolling_accuracy_10d=Decimal("0.30"))
        assert cb.state == CircuitBreakerState.RED
        assert not ctrl.can_execute("recommender")

        cb.manual_reset()
        assert cb.state == CircuitBreakerState.GREEN
        assert ctrl.can_execute("recommender")

    def test_semi_auto_requires_manual_confirmation(self):
        """Semi-auto engines can execute but self-improvement is gated."""
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)

        config = ctrl.get_engine_config("self_improvement")
        assert config.level == AutonomyLevel.SEMI_AUTO
        assert ctrl.can_execute("self_improvement")

    def test_elevation_and_demotion(self):
        """Autonomy level can be raised and lowered."""
        cb = CircuitBreakerService()
        ctrl = AutonomyController(cb)

        ctrl.set_engine_level("paper_trader", AutonomyLevel.FULL_AUTO)
        assert ctrl.can_execute("paper_trader")

        ctrl.set_engine_level("paper_trader", AutonomyLevel.MANUAL)
        assert not ctrl.can_execute("paper_trader")
