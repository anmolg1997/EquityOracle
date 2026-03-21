"""Overfitting detection — Deflated Sharpe, IS/OOS ratio, feature stability."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class OverfittingReport:
    is_overfitting: bool
    deflated_sharpe: float
    is_oos_ratio: float
    feature_stability: float
    warnings: list[str]


def detect_overfitting(
    in_sample_sharpe: float,
    out_of_sample_sharpe: float,
    n_trials: int = 1,
    n_observations: int = 252,
    feature_importance_folds: list[dict[str, float]] | None = None,
    is_oos_max_ratio: float = 2.0,
) -> OverfittingReport:
    """Comprehensive overfitting detection.

    Checks:
    1. Deflated Sharpe Ratio (adjusts for multiple testing)
    2. In-sample vs out-of-sample Sharpe ratio
    3. Feature importance stability across folds
    """
    warnings: list[str] = []

    # 1. Deflated Sharpe Ratio
    deflated = compute_deflated_sharpe(in_sample_sharpe, n_trials, n_observations)
    if deflated < 0.5:
        warnings.append(f"Deflated Sharpe ({deflated:.2f}) below threshold — may be luck, not skill")

    # 2. IS/OOS ratio
    is_oos_ratio = in_sample_sharpe / max(out_of_sample_sharpe, 0.01)
    if is_oos_ratio > is_oos_max_ratio:
        warnings.append(
            f"IS/OOS Sharpe ratio {is_oos_ratio:.1f}x exceeds {is_oos_max_ratio}x threshold"
        )

    # 3. Feature importance stability
    feature_stability = 1.0
    if feature_importance_folds and len(feature_importance_folds) >= 2:
        feature_stability = compute_feature_stability(feature_importance_folds)
        if feature_stability < 0.5:
            warnings.append(
                f"Feature importance stability {feature_stability:.2f} — top features change across folds"
            )

    is_overfitting = len(warnings) >= 2

    return OverfittingReport(
        is_overfitting=is_overfitting,
        deflated_sharpe=deflated,
        is_oos_ratio=is_oos_ratio,
        feature_stability=feature_stability,
        warnings=warnings,
    )


def compute_deflated_sharpe(
    sharpe: float,
    n_trials: int,
    n_observations: int,
) -> float:
    """Adjust Sharpe ratio for multiple testing (Bailey & López de Prado).

    The idea: if you test N strategies, the best one will look good by luck.
    Deflated Sharpe adjusts for this.
    """
    if n_trials <= 1:
        return sharpe

    euler_mascheroni = 0.5772
    expected_max_sharpe = (
        (1 - euler_mascheroni) * _norm_ppf(1 - 1 / n_trials)
        + euler_mascheroni * _norm_ppf(1 - 1 / (n_trials * np.e))
    )

    se = np.sqrt(1 / n_observations)
    deflated = (sharpe - expected_max_sharpe) / se
    from scipy.stats import norm
    return float(norm.cdf(deflated))


def compute_feature_stability(
    importance_folds: list[dict[str, float]],
    top_k: int = 10,
) -> float:
    """Measure how stable top features are across CV folds.

    Returns a score from 0 (completely unstable) to 1 (perfectly stable).
    """
    top_sets: list[set[str]] = []
    for imp in importance_folds:
        sorted_features = sorted(imp.items(), key=lambda x: x[1], reverse=True)
        top_sets.append({f for f, _ in sorted_features[:top_k]})

    if len(top_sets) < 2:
        return 1.0

    overlaps: list[float] = []
    for i in range(len(top_sets)):
        for j in range(i + 1, len(top_sets)):
            overlap = len(top_sets[i] & top_sets[j]) / top_k
            overlaps.append(overlap)

    return float(np.mean(overlaps))


def _norm_ppf(p: float) -> float:
    """Normal distribution percent point function (inverse CDF)."""
    from scipy.stats import norm
    return float(norm.ppf(p))
