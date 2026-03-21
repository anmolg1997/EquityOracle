"""Autonomy controller — per-engine flags integrated with circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.core.types import AutonomyLevel, CircuitBreakerState
from app.domain.risk.circuit_breaker import CircuitBreakerService

log = get_logger(__name__)


@dataclass
class EngineConfig:
    name: str
    level: AutonomyLevel = AutonomyLevel.MANUAL
    description: str = ""


class AutonomyController:
    """Manages autonomy levels per engine, integrated with circuit breaker."""

    def __init__(self, circuit_breaker: CircuitBreakerService) -> None:
        self._cb = circuit_breaker
        self._engines: dict[str, EngineConfig] = {
            "scanner": EngineConfig("scanner", AutonomyLevel.FULL_AUTO, "Scanning is always automated"),
            "recommender": EngineConfig("recommender", AutonomyLevel.SEMI_AUTO, "Recs generated, human approves trades"),
            "paper_trader": EngineConfig("paper_trader", AutonomyLevel.MANUAL, "Manual paper trading"),
            "self_improvement": EngineConfig("self_improvement", AutonomyLevel.SEMI_AUTO, "Proposes changes, human confirms"),
        }

    def can_execute(self, engine: str) -> bool:
        """Check if an engine can execute autonomously given current state."""
        config = self._engines.get(engine)
        if not config:
            return False

        if config.level == AutonomyLevel.MANUAL:
            return False

        # Circuit breaker override
        cb_state = self._cb.state
        if cb_state == CircuitBreakerState.BLACK:
            return False
        if cb_state == CircuitBreakerState.RED and engine in ("paper_trader", "recommender"):
            return False

        return True

    def get_engine_config(self, engine: str) -> EngineConfig | None:
        return self._engines.get(engine)

    def set_engine_level(self, engine: str, level: AutonomyLevel) -> None:
        if engine in self._engines:
            self._engines[engine].level = level
            log.info("autonomy_updated", engine=engine, level=level.value)

    def get_all_configs(self) -> dict[str, dict]:
        return {
            name: {
                "level": config.level.value,
                "description": config.description,
                "can_execute": self.can_execute(name),
                "circuit_breaker": self._cb.state.value,
            }
            for name, config in self._engines.items()
        }
