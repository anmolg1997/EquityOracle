"""Tests for survivorship-bias-free universe management."""

from datetime import date

from app.ml.safeguards.universe_manager import UniverseManager


class TestUniverseManager:
    def test_record_and_retrieve(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 1, 1), ["AAPL", "GOOG", "MSFT"])

        snap = mgr.get_universe(date(2024, 1, 1))
        assert "AAPL" in snap.tickers
        assert len(snap.tickers) == 3

    def test_retrieves_nearest_past_snapshot(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 1, 1), ["A", "B"])
        mgr.record_universe(date(2024, 3, 1), ["A", "C"])

        snap = mgr.get_universe(date(2024, 2, 15))
        assert "A" in snap.tickers
        assert "B" in snap.tickers
        assert "C" not in snap.tickers

    def test_includes_delisted_stocks_for_historical_date(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 1, 1), ["A", "B"])
        mgr.record_delisting("C", delisted_on=date(2024, 6, 1))

        snap = mgr.get_universe(date(2024, 3, 1))
        assert "C" in snap.tickers
        assert snap.delisted_included == 1

    def test_delisted_stock_excluded_after_delisting(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 1, 1), ["A", "B"])
        mgr.record_delisting("C", delisted_on=date(2024, 3, 1))

        snap = mgr.get_universe(date(2024, 6, 1))
        assert "C" not in snap.tickers

    def test_empty_universe_for_early_date(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 6, 1), ["A"])

        snap = mgr.get_universe(date(2024, 1, 1))
        assert len(snap.tickers) == 0


class TestSurvivorshipBiasCheck:
    def test_no_bias_when_complete(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 1, 1), ["A", "B", "C"])

        result = mgr.check_survivorship_bias(
            training_tickers=["A", "B", "C"],
            training_start=date(2024, 1, 1),
            training_end=date(2024, 6, 1),
        )
        assert result["check"] == "completed"
        assert not result["is_biased"]
        assert result["survivorship_bias_score"] == 0

    def test_bias_detected_when_delisted_missing(self):
        mgr = UniverseManager()
        mgr.record_universe(date(2024, 1, 1), ["A", "B", "C", "D", "E"])
        mgr.record_delisting("D", date(2024, 3, 1))
        mgr.record_delisting("E", date(2024, 4, 1))

        result = mgr.check_survivorship_bias(
            training_tickers=["A", "B", "C"],
            training_start=date(2024, 1, 1),
            training_end=date(2024, 6, 1),
        )
        assert result["check"] == "completed"
        assert result["delisted_missing"] == 2
        assert result["is_biased"]

    def test_no_historical_data_skips(self):
        mgr = UniverseManager()
        result = mgr.check_survivorship_bias(
            training_tickers=["A"],
            training_start=date(2024, 1, 1),
            training_end=date(2024, 6, 1),
        )
        assert result["check"] == "skipped"
