"""Calibration evaluation — predicted vs actual return/probability curves."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CalibrationBucket:
    predicted_range: tuple[float, float]
    n_samples: int
    predicted_mean: float
    actual_mean: float
    error: float


@dataclass
class CalibrationReport:
    buckets: list[CalibrationBucket]
    expected_calibration_error: float
    is_well_calibrated: bool


def evaluate_calibration(
    predicted_probabilities: list[float],
    actual_outcomes: list[int],
    n_bins: int = 10,
) -> CalibrationReport:
    """Evaluate probability calibration: "When model says 70% confident,
    is it right 70% of the time?"
    """
    pred = np.array(predicted_probabilities)
    actual = np.array(actual_outcomes)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    buckets: list[CalibrationBucket] = []
    total_ece = 0.0

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (pred >= lo) & (pred < hi) if i < n_bins - 1 else (pred >= lo) & (pred <= hi)

        n = int(mask.sum())
        if n == 0:
            continue

        pred_mean = float(pred[mask].mean())
        actual_mean = float(actual[mask].mean())
        error = abs(pred_mean - actual_mean)

        buckets.append(CalibrationBucket(
            predicted_range=(round(lo, 2), round(hi, 2)),
            n_samples=n,
            predicted_mean=round(pred_mean, 4),
            actual_mean=round(actual_mean, 4),
            error=round(error, 4),
        ))

        total_ece += error * n / len(pred)

    return CalibrationReport(
        buckets=buckets,
        expected_calibration_error=round(total_ece, 4),
        is_well_calibrated=total_ece < 0.1,
    )
