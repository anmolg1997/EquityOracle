"""Signal decorrelation check — ensures pillar independence.

Computes pairwise rank correlation between pillar scores across the
universe. If two pillars are >0.75 correlated, down-weights the
redundant one. Exposes effective independent signal count.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np


@dataclass
class DecorrelationResult:
    pairwise_correlations: dict[str, float]
    effective_signal_count: Decimal
    adjustments: dict[str, float]


def compute_decorrelation(
    pillar_scores: dict[str, list[float]],
    correlation_threshold: float = 0.75,
) -> DecorrelationResult:
    """Compute pairwise rank correlations between scoring pillars.

    Args:
        pillar_scores: {pillar_name: [scores_for_universe]} — same ordering.
        correlation_threshold: Above this, pillars are considered redundant.

    Returns:
        DecorrelationResult with pairwise correlations, effective signal count,
        and per-pillar adjustment factors.
    """
    pillars = list(pillar_scores.keys())
    n = len(pillars)

    if n < 2:
        return DecorrelationResult(
            pairwise_correlations={},
            effective_signal_count=Decimal(str(n)),
            adjustments={p: 1.0 for p in pillars},
        )

    scores_matrix = np.array([pillar_scores[p] for p in pillars])

    rank_matrix = np.zeros_like(scores_matrix)
    for i in range(n):
        rank_matrix[i] = _rankdata(scores_matrix[i])

    pairwise: dict[str, float] = {}
    redundancy_flags: dict[str, bool] = {p: False for p in pillars}

    for i in range(n):
        for j in range(i + 1, n):
            corr = float(np.corrcoef(rank_matrix[i], rank_matrix[j])[0, 1])
            if np.isnan(corr):
                corr = 0.0
            key = f"{pillars[i]}_vs_{pillars[j]}"
            pairwise[key] = round(corr, 4)

            if abs(corr) > correlation_threshold:
                redundancy_flags[pillars[j]] = True

    adjustments: dict[str, float] = {}
    effective = 0.0
    for p in pillars:
        if redundancy_flags[p]:
            adjustments[p] = 0.5
            effective += 0.5
        else:
            adjustments[p] = 1.0
            effective += 1.0

    return DecorrelationResult(
        pairwise_correlations=pairwise,
        effective_signal_count=Decimal(str(round(effective, 1))),
        adjustments=adjustments,
    )


def _rankdata(arr: np.ndarray) -> np.ndarray:
    """Simple rank assignment (average method)."""
    temp = arr.argsort()
    ranks = np.empty_like(temp, dtype=float)
    ranks[temp] = np.arange(1, len(arr) + 1, dtype=float)
    return ranks
