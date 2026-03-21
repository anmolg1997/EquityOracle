"""Decision audit trail — log full context per recommendation."""

from __future__ import annotations

from app.core.logging import get_logger
from app.domain.recommendation.models import DecisionAudit

log = get_logger(__name__)

_audit_log: list[DecisionAudit] = []


def record_audit(audit: DecisionAudit) -> None:
    """Record a decision audit entry."""
    _audit_log.append(audit)
    log.info(
        "decision_audit",
        correlation_id=audit.correlation_id,
        ticker=str(audit.ticker),
        decision=audit.decision.value,
        composite_score=str(audit.composite_score),
        confidence=str(audit.confidence),
        effective_signals=str(audit.effective_signal_count),
    )


def get_audit_trail(correlation_id: str | None = None) -> list[DecisionAudit]:
    if correlation_id:
        return [a for a in _audit_log if a.correlation_id == correlation_id]
    return list(_audit_log)
