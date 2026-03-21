"""Self-improvement with Bayesian weight adjustment, minimum sample enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class ImprovementProposal:
    old_weights: dict[str, float]
    new_weights: dict[str, float]
    sample_size: int
    evidence: dict
    approved: bool = False
    reason: str = ""


class SelfImprovementService:
    """Adjusts composite weights based on historical accuracy.

    Safeguards:
    - Minimum 100 samples per bucket before any adjustment
    - Maximum 5 percentage point change per pillar
    - Bayesian shrinkage toward current weights
    - Immutable change log
    """

    MIN_SAMPLE_SIZE = 100
    MAX_CHANGE_PCT = 0.05
    SHRINKAGE_FACTOR = 0.3  # blend 30% toward evidence, 70% prior

    def __init__(self) -> None:
        self._change_log: list[ImprovementProposal] = []

    def propose_adjustment(
        self,
        current_weights: dict[str, float],
        pillar_accuracy: dict[str, float],
        sample_counts: dict[str, int],
    ) -> ImprovementProposal:
        """Propose weight adjustments based on pillar performance."""
        # Check minimum sample size
        min_samples = min(sample_counts.values()) if sample_counts else 0
        if min_samples < self.MIN_SAMPLE_SIZE:
            return ImprovementProposal(
                old_weights=current_weights,
                new_weights=current_weights,
                sample_size=min_samples,
                evidence=pillar_accuracy,
                approved=False,
                reason=f"Insufficient samples: {min_samples} < {self.MIN_SAMPLE_SIZE}",
            )

        # Compute evidence-based weights (normalize accuracy to weights)
        total_accuracy = sum(pillar_accuracy.values())
        if total_accuracy == 0:
            return ImprovementProposal(
                old_weights=current_weights,
                new_weights=current_weights,
                sample_size=min_samples,
                evidence=pillar_accuracy,
                approved=False,
                reason="Zero total accuracy",
            )

        evidence_weights = {k: v / total_accuracy for k, v in pillar_accuracy.items()}

        # Bayesian shrinkage: blend toward evidence
        new_weights: dict[str, float] = {}
        for pillar in current_weights:
            prior = current_weights[pillar]
            evidence = evidence_weights.get(pillar, prior)
            blended = prior * (1 - self.SHRINKAGE_FACTOR) + evidence * self.SHRINKAGE_FACTOR

            # Cap change
            change = blended - prior
            if abs(change) > self.MAX_CHANGE_PCT:
                change = self.MAX_CHANGE_PCT if change > 0 else -self.MAX_CHANGE_PCT
                blended = prior + change

            new_weights[pillar] = round(blended, 4)

        # Normalize
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: round(v / total, 4) for k, v in new_weights.items()}

        proposal = ImprovementProposal(
            old_weights=current_weights,
            new_weights=new_weights,
            sample_size=min_samples,
            evidence=pillar_accuracy,
            approved=True,
        )
        self._change_log.append(proposal)

        log.info("weight_proposal", old=current_weights, new=new_weights, samples=min_samples)
        return proposal

    @property
    def change_log(self) -> list[ImprovementProposal]:
        return list(self._change_log)
