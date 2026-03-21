"""Ensemble combiner — weighted average + confidence from model disagreement."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np


@dataclass
class EnsemblePrediction:
    expected_return: Decimal
    direction_probability: Decimal
    confidence: Decimal
    model_agreement: Decimal
    individual_predictions: dict[str, dict]


class EnsembleCombiner:
    """Combines predictions from multiple models using weighted averaging.

    Confidence is derived from model agreement — if models disagree,
    confidence is lower regardless of individual model confidence.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or {"xgboost": 0.6, "lstm": 0.4}

    def combine(
        self,
        predictions: dict[str, dict],
    ) -> EnsemblePrediction:
        """Combine predictions from multiple models.

        predictions: {model_name: {"expected_return": float, "direction_probability": float, "confidence": float}}
        """
        if not predictions:
            return EnsemblePrediction(
                expected_return=Decimal(0),
                direction_probability=Decimal("0.5"),
                confidence=Decimal(0),
                model_agreement=Decimal(0),
                individual_predictions={},
            )

        total_weight = 0.0
        weighted_return = 0.0
        weighted_dir_prob = 0.0
        weighted_confidence = 0.0
        dir_probs: list[float] = []

        for model_name, pred in predictions.items():
            w = self._weights.get(model_name, 1.0 / len(predictions))
            total_weight += w
            weighted_return += pred["expected_return"] * w
            weighted_dir_prob += pred["direction_probability"] * w
            weighted_confidence += pred["confidence"] * w
            dir_probs.append(pred["direction_probability"])

        if total_weight > 0:
            weighted_return /= total_weight
            weighted_dir_prob /= total_weight
            weighted_confidence /= total_weight

        agreement = 1.0 - np.std(dir_probs) * 2 if len(dir_probs) > 1 else 1.0
        agreement = max(0.0, min(1.0, agreement))

        # Final confidence = average of individual confidence * agreement
        final_confidence = weighted_confidence * agreement

        return EnsemblePrediction(
            expected_return=Decimal(str(round(weighted_return, 6))),
            direction_probability=Decimal(str(round(weighted_dir_prob, 4))),
            confidence=Decimal(str(round(final_confidence, 4))),
            model_agreement=Decimal(str(round(agreement, 4))),
            individual_predictions=predictions,
        )
