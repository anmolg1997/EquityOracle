"""Tests for feature importance attribution tracking."""

from app.ml.evaluation.attribution import compute_attribution


class TestAttribution:
    def test_top_k_features(self):
        importances = {f"feature_{i}": float(i) for i in range(30)}
        report = compute_attribution(importances, top_k=10)
        assert len(report.top_features) == 10
        assert report.top_features[0].rank == 1
        assert report.top_features[0].importance > report.top_features[1].importance

    def test_category_classification_technical(self):
        importances = {"rsi_14": 0.3, "macd_signal": 0.2, "volume_ratio": 0.1}
        report = compute_attribution(importances, top_k=3)
        for feat in report.top_features:
            assert feat.category == "technical"
        assert "technical" in report.category_weights

    def test_category_classification_fundamental(self):
        importances = {"pe_ratio": 0.4, "roe_3yr": 0.3, "debt_to_equity": 0.2}
        report = compute_attribution(importances, top_k=3)
        for feat in report.top_features:
            assert feat.category == "fundamental"

    def test_category_classification_alternative(self):
        importances = {"custom_signal": 0.5, "macro_index": 0.3}
        report = compute_attribution(importances, top_k=2)
        for feat in report.top_features:
            assert feat.category == "alternative"

    def test_mixed_categories(self):
        importances = {"rsi_14": 0.3, "pe_ratio": 0.3, "custom": 0.3}
        report = compute_attribution(importances, top_k=3)
        categories = {f.category for f in report.top_features}
        assert len(categories) == 3

    def test_empty_importances(self):
        report = compute_attribution({}, top_k=5)
        assert len(report.top_features) == 0

    def test_category_weights_sum_to_one(self):
        importances = {"rsi_14": 0.3, "pe_ratio": 0.2, "custom": 0.5}
        report = compute_attribution(importances, top_k=3)
        total = sum(report.category_weights.values())
        assert abs(total - 1.0) < 0.01
