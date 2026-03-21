"""Tests for point-in-time enforcement — lookahead prevention."""

from datetime import date

import pandas as pd
import pytest

from app.core.exceptions import LookaheadBiasError
from app.ml.safeguards.point_in_time import (
    enforce_point_in_time,
    validate_point_in_time,
)


def test_valid_point_in_time():
    df = pd.DataFrame({
        "feature_a": [1, 2, 3],
        "available_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    })
    result = validate_point_in_time(df, date(2024, 1, 5))
    assert result.is_valid


def test_lookahead_detected():
    df = pd.DataFrame({
        "feature_a": [1, 2, 3],
        "available_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-10"]),
    })
    result = validate_point_in_time(df, date(2024, 1, 5))
    assert not result.is_valid
    assert len(result.violations) > 0


def test_enforce_strict_raises():
    df = pd.DataFrame({
        "feature_a": [1, 2, 3],
        "available_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-10"]),
    })
    with pytest.raises(LookaheadBiasError):
        enforce_point_in_time(df, date(2024, 1, 5), strict=True)


def test_enforce_non_strict_filters():
    df = pd.DataFrame({
        "feature_a": [1, 2, 3],
        "available_at": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-10"]),
    })
    filtered = enforce_point_in_time(df, date(2024, 1, 5), strict=False)
    assert len(filtered) == 2
