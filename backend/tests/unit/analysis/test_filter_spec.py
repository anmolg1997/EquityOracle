"""Tests for FilterSpec builder and evaluation."""

from app.application.scanner.filter_spec import FilterSpec


class TestFilterSpecBuilding:
    def test_add_criteria(self):
        spec = FilterSpec(name="test")
        spec.add("rsi", ">", 50)
        assert len(spec.criteria) == 1
        assert spec.criteria[0].field == "rsi"

    def test_chaining(self):
        spec = FilterSpec(name="test")
        result = spec.add("rsi", ">", 50).add("volume", ">=", 1000)
        assert result is spec
        assert len(spec.criteria) == 2


class TestFilterSpecEvaluation:
    def test_gt_passes(self):
        spec = FilterSpec()
        spec.add("rsi", ">", 50)
        assert spec.evaluate({"rsi": 60})

    def test_gt_fails(self):
        spec = FilterSpec()
        spec.add("rsi", ">", 50)
        assert not spec.evaluate({"rsi": 40})

    def test_gte(self):
        spec = FilterSpec()
        spec.add("volume", ">=", 1000)
        assert spec.evaluate({"volume": 1000})
        assert not spec.evaluate({"volume": 999})

    def test_lt(self):
        spec = FilterSpec()
        spec.add("pe", "<", 20)
        assert spec.evaluate({"pe": 15})
        assert not spec.evaluate({"pe": 25})

    def test_lte(self):
        spec = FilterSpec()
        spec.add("pe", "<=", 20)
        assert spec.evaluate({"pe": 20})

    def test_eq(self):
        spec = FilterSpec()
        spec.add("category", "==", 1)
        assert spec.evaluate({"category": 1})
        assert not spec.evaluate({"category": 2})

    def test_between(self):
        spec = FilterSpec()
        spec.add("rsi", "between", min=30, max=70)
        assert spec.evaluate({"rsi": 50})
        assert not spec.evaluate({"rsi": 80})
        assert not spec.evaluate({"rsi": 20})

    def test_above_pct(self):
        spec = FilterSpec()
        spec.add("close", "above_pct", 10, reference="sma_200")
        assert spec.evaluate({"close": 120, "sma_200": 100})
        assert not spec.evaluate({"close": 105, "sma_200": 100})

    def test_within_pct(self):
        spec = FilterSpec()
        spec.add("close", "within_pct", 5, reference="high_52w")
        assert spec.evaluate({"close": 97, "high_52w": 100})
        assert not spec.evaluate({"close": 90, "high_52w": 100})

    def test_missing_field_fails(self):
        spec = FilterSpec()
        spec.add("rsi", ">", 50)
        assert not spec.evaluate({"volume": 100})

    def test_missing_reference_fails(self):
        spec = FilterSpec()
        spec.add("close", "above_pct", 10, reference="sma_200")
        assert not spec.evaluate({"close": 120})

    def test_multiple_criteria_all_must_pass(self):
        spec = FilterSpec()
        spec.add("rsi", ">", 50).add("volume", ">=", 1000)
        assert spec.evaluate({"rsi": 60, "volume": 2000})
        assert not spec.evaluate({"rsi": 60, "volume": 500})
        assert not spec.evaluate({"rsi": 40, "volume": 2000})

    def test_reference_with_multiplier(self):
        spec = FilterSpec()
        spec.add("close", ">", reference="sma_50", multiplier=1.1)
        assert spec.evaluate({"close": 120, "sma_50": 100})
        assert not spec.evaluate({"close": 105, "sma_50": 100})
