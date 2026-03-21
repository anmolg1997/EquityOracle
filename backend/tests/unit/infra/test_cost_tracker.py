"""Tests for LLM cost tracker — budget, usage recording, local fallback."""

from app.infrastructure.llm.cost_tracker import LLMCostTracker


class TestCostTracker:
    def test_initial_budget(self):
        tracker = LLMCostTracker(daily_budget_inr=100.0)
        assert tracker.budget_remaining == 100.0
        assert tracker.today_spend == 0.0

    def test_record_usage_increases_spend(self):
        tracker = LLMCostTracker(daily_budget_inr=100.0)
        entry = tracker.record_usage("gemini/gemini-2.0-flash", 1000, 500, "thesis")
        assert entry.cost_inr > 0
        assert tracker.today_spend > 0

    def test_budget_decreases_after_usage(self):
        tracker = LLMCostTracker(daily_budget_inr=100.0)
        tracker.record_usage("gemini/gemini-2.0-flash", 1000, 500, "debate")
        assert tracker.budget_remaining < 100.0

    def test_can_afford_within_budget(self):
        tracker = LLMCostTracker(daily_budget_inr=100.0)
        assert tracker.can_afford(1.0)

    def test_cannot_afford_exceeds_budget(self):
        tracker = LLMCostTracker(daily_budget_inr=0.001)
        assert not tracker.can_afford(1.0)

    def test_ollama_is_free(self):
        tracker = LLMCostTracker(daily_budget_inr=100.0)
        entry = tracker.record_usage("ollama/llama3.2", 10000, 5000, "thesis")
        assert entry.cost_inr == 0.0

    def test_should_use_local_when_budget_low(self):
        tracker = LLMCostTracker(daily_budget_inr=1.0)
        tracker.record_usage("gemini/gemini-1.5-pro", 100000, 50000, "debate")
        assert tracker.should_use_local()

    def test_daily_summary(self):
        tracker = LLMCostTracker(daily_budget_inr=50.0)
        tracker.record_usage("gemini/gemini-2.0-flash", 500, 200, "test")
        summary = tracker.get_daily_summary()
        assert summary["calls"] == 1
        assert summary["budget_inr"] == 50.0
        assert summary["total_tokens"] == 700

    def test_unknown_model_uses_default_pricing(self):
        tracker = LLMCostTracker(daily_budget_inr=100.0)
        entry = tracker.record_usage("unknown/model", 1000, 1000, "test")
        assert entry.cost_inr > 0
