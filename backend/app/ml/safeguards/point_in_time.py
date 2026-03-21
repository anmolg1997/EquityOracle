"""Point-in-time enforcement — prevent lookahead bias in feature engineering.

Every feature must carry an available_at timestamp. This module verifies
that no feature at time T uses data with available_at > T.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from app.core.exceptions import LookaheadBiasError
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class PITValidationResult:
    is_valid: bool
    violations: list[str]
    total_features_checked: int


def validate_point_in_time(
    features: pd.DataFrame,
    prediction_date: date,
    available_at_column: str = "available_at",
) -> PITValidationResult:
    """Validate that all features respect point-in-time constraints.

    Checks that no feature row has available_at > prediction_date.
    """
    violations: list[str] = []

    if available_at_column in features.columns:
        future_data = features[features[available_at_column] > pd.Timestamp(prediction_date)]
        if len(future_data) > 0:
            violations.append(
                f"Found {len(future_data)} rows with available_at after {prediction_date}"
            )

    return PITValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        total_features_checked=len(features.columns),
    )


def enforce_point_in_time(
    features: pd.DataFrame,
    prediction_date: date,
    available_at_column: str = "available_at",
    strict: bool = True,
) -> pd.DataFrame:
    """Filter features to only include data available at prediction_date.

    In strict mode, raises LookaheadBiasError if violations are found.
    In non-strict mode, silently filters out future data.
    """
    if available_at_column not in features.columns:
        return features

    future_mask = features[available_at_column] > pd.Timestamp(prediction_date)
    violation_count = future_mask.sum()

    if violation_count > 0:
        if strict:
            raise LookaheadBiasError(
                f"Lookahead bias detected: {violation_count} features use data "
                f"not available at {prediction_date}",
                details={"violation_count": violation_count},
            )
        log.warning(
            "lookahead_filtered",
            violations=int(violation_count),
            prediction_date=str(prediction_date),
        )

    return features[~future_mask].copy()


def create_training_labels(
    ohlcv_df: pd.DataFrame,
    horizon_days: int,
) -> tuple[pd.Series, pd.Series]:
    """Create direction and return labels for supervised learning.

    Labels are based on future returns (which is correct for training —
    we're not using these as features).
    """
    future_return = ohlcv_df["close"].pct_change(horizon_days).shift(-horizon_days)
    direction = (future_return > 0).astype(int)

    return direction, future_return
