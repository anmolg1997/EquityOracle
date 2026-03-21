"""Tests for shadow A/B testing service — parallel weight comparison."""

import numpy as np

from app.application.autonomy.ab_testing import ABTestingService


class TestABTestingService:
    def test_start_test(self):
        svc = ABTestingService()
        svc.start_test({"a": 0.5, "b": 0.5})
        assert svc._shadow is not None
        assert svc._shadow.weights == {"a": 0.5, "b": 0.5}

    def test_record_daily_without_test_noop(self):
        svc = ABTestingService()
        svc.record_daily(0.01, 0.02)

    def test_evaluate_returns_none_before_min_duration(self):
        svc = ABTestingService()
        svc.start_test({"a": 0.6, "b": 0.4})
        for _ in range(10):
            svc.record_daily(0.001, 0.002)
        result = svc.evaluate()
        assert result is None

    def test_evaluate_after_min_duration(self):
        svc = ABTestingService()
        svc.start_test({"a": 0.6, "b": 0.4})
        np.random.seed(42)
        for _ in range(20):
            svc.record_daily(
                float(np.random.normal(0.001, 0.01)),
                float(np.random.normal(0.003, 0.01)),
            )
        result = svc.evaluate()
        assert result is not None
        assert result.duration_days == 20

    def test_significant_improvement_adopted(self):
        svc = ABTestingService()
        svc.start_test({"a": 0.7, "b": 0.3})
        np.random.seed(42)
        for _ in range(30):
            svc.record_daily(
                float(np.random.normal(-0.005, 0.001)),
                float(np.random.normal(0.005, 0.001)),
            )
        result = svc.evaluate()
        assert result is not None
        assert result.is_significant
        assert result.recommendation == "adopt"
        assert result.delta > 0

    def test_no_improvement_rejected(self):
        svc = ABTestingService()
        svc.start_test({"a": 0.5, "b": 0.5})
        np.random.seed(42)
        for _ in range(20):
            val = float(np.random.normal(0.001, 0.01))
            svc.record_daily(val, val)
        result = svc.evaluate()
        assert result is not None
        assert result.recommendation == "reject"

    def test_reset_clears_state(self):
        svc = ABTestingService()
        svc.start_test({"a": 0.6, "b": 0.4})
        svc.record_daily(0.001, 0.002)
        svc.reset()
        assert svc._shadow is None
        assert svc._live_returns == []

    def test_evaluate_without_test_returns_none(self):
        svc = ABTestingService()
        result = svc.evaluate()
        assert result is None
