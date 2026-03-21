"""Extended tests for point-in-time module — training labels and edge cases."""

from datetime import date

import pandas as pd

from app.ml.safeguards.point_in_time import (
    create_training_labels,
    validate_point_in_time,
)


class TestCreateTrainingLabels:
    def test_creates_direction_labels(self):
        df = pd.DataFrame({
            "close": [100, 105, 110, 108, 112, 115, 118, 120, 125, 130],
        })
        direction, returns = create_training_labels(df, horizon_days=1)
        assert len(direction) == 10
        assert direction.dtype == int

    def test_positive_return_is_1(self):
        df = pd.DataFrame({"close": [100, 110]})
        direction, returns = create_training_labels(df, horizon_days=1)
        assert direction.iloc[0] == 1

    def test_negative_return_is_0(self):
        df = pd.DataFrame({"close": [110, 100]})
        direction, returns = create_training_labels(df, horizon_days=1)
        assert direction.iloc[0] == 0

    def test_nan_at_end_of_series(self):
        df = pd.DataFrame({"close": [100, 105, 110, 115, 120]})
        direction, returns = create_training_labels(df, horizon_days=2)
        assert pd.isna(returns.iloc[-1])
        assert pd.isna(returns.iloc[-2])


class TestValidationEdgeCases:
    def test_no_available_at_column_passes(self):
        df = pd.DataFrame({"feature_a": [1, 2, 3]})
        result = validate_point_in_time(df, date(2024, 1, 5))
        assert result.is_valid

    def test_all_data_at_exact_date_passes(self):
        df = pd.DataFrame({
            "feature_a": [1, 2, 3],
            "available_at": pd.to_datetime(["2024-01-05"] * 3),
        })
        result = validate_point_in_time(df, date(2024, 1, 5))
        assert result.is_valid

    def test_empty_dataframe_passes(self):
        df = pd.DataFrame({"available_at": pd.Series([], dtype="datetime64[ns]")})
        result = validate_point_in_time(df, date(2024, 1, 5))
        assert result.is_valid
