"""Tests for overfitting detection — Deflated Sharpe, IS/OOS, feature stability."""

from app.ml.safeguards.overfitting_detector import (
    compute_feature_stability,
    detect_overfitting,
)


class TestOverfittingDetection:
    def test_healthy_model_no_overfitting(self):
        report = detect_overfitting(
            in_sample_sharpe=1.5,
            out_of_sample_sharpe=1.2,
            n_trials=1,
            n_observations=252,
        )
        assert not report.is_overfitting
        assert report.is_oos_ratio < 2.0

    def test_high_is_oos_ratio_flagged(self):
        report = detect_overfitting(
            in_sample_sharpe=3.0,
            out_of_sample_sharpe=0.5,
            n_trials=1,
            n_observations=252,
        )
        assert report.is_oos_ratio > 2.0
        assert any("IS/OOS" in w for w in report.warnings)

    def test_multiple_trials_deflate_sharpe(self):
        report = detect_overfitting(
            in_sample_sharpe=1.5,
            out_of_sample_sharpe=1.3,
            n_trials=100,
            n_observations=252,
        )
        assert report.deflated_sharpe < 1.0

    def test_two_warnings_triggers_overfitting(self):
        unstable_folds = [
            {"a": 0.9, "b": 0.1},
            {"c": 0.9, "d": 0.1},
        ]
        report = detect_overfitting(
            in_sample_sharpe=3.0,
            out_of_sample_sharpe=0.3,
            n_trials=1,
            n_observations=252,
            feature_importance_folds=unstable_folds,
        )
        assert report.is_overfitting
        assert len(report.warnings) >= 2


class TestFeatureStability:
    def test_perfectly_stable_features(self):
        folds = [
            {"rsi": 0.5, "macd": 0.3, "volume": 0.2},
            {"rsi": 0.5, "macd": 0.3, "volume": 0.2},
            {"rsi": 0.5, "macd": 0.3, "volume": 0.2},
        ]
        stability = compute_feature_stability(folds, top_k=3)
        assert stability == 1.0

    def test_completely_unstable_features(self):
        folds = [
            {"a": 0.9, "b": 0.1},
            {"c": 0.9, "d": 0.1},
            {"e": 0.9, "f": 0.1},
        ]
        stability = compute_feature_stability(folds, top_k=2)
        assert stability == 0.0

    def test_partial_stability(self):
        folds = [
            {"rsi": 0.5, "macd": 0.3, "adx": 0.2},
            {"rsi": 0.5, "adx": 0.3, "bb": 0.2},
        ]
        stability = compute_feature_stability(folds, top_k=3)
        assert 0 < stability < 1

    def test_single_fold_returns_1(self):
        folds = [{"rsi": 0.5, "macd": 0.3}]
        stability = compute_feature_stability(folds, top_k=2)
        assert stability == 1.0

    def test_unstable_features_flagged_in_detection(self):
        folds = [
            {"a": 0.9, "b": 0.1},
            {"c": 0.9, "d": 0.1},
        ]
        report = detect_overfitting(
            in_sample_sharpe=1.5,
            out_of_sample_sharpe=1.3,
            n_trials=1,
            feature_importance_folds=folds,
        )
        assert report.feature_stability == 0.0
        assert any("stability" in w.lower() for w in report.warnings)
