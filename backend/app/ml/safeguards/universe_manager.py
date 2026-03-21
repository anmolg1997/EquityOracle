"""Survivorship-bias-free point-in-time stock universe management.

Tracks which stocks were listed on any given historical date,
including stocks that have since been delisted. This prevents
training models only on survivors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class UniverseSnapshot:
    as_of_date: date
    tickers: list[str]
    delisted_included: int = 0


class UniverseManager:
    """Maintains historical universe snapshots for bias-free training.

    In production, this should be backed by persistent storage with
    historical listing/delisting dates from exchange data.
    """

    def __init__(self) -> None:
        self._snapshots: dict[date, list[str]] = {}
        self._delisted: dict[str, date] = {}  # ticker -> delisting date

    def record_universe(self, as_of: date, tickers: list[str]) -> None:
        self._snapshots[as_of] = tickers

    def record_delisting(self, ticker: str, delisted_on: date) -> None:
        self._delisted[ticker] = delisted_on

    def get_universe(self, as_of: date) -> UniverseSnapshot:
        """Get the universe as it existed on a given date.

        Includes stocks that were listed on that date even if
        they have since been delisted.
        """
        # Find nearest snapshot on or before as_of
        available_dates = sorted(d for d in self._snapshots if d <= as_of)
        if not available_dates:
            return UniverseSnapshot(as_of_date=as_of, tickers=[])

        nearest = available_dates[-1]
        tickers = self._snapshots[nearest]

        # Include delisted stocks that were active on as_of
        delisted_count = 0
        for ticker, delist_date in self._delisted.items():
            if delist_date > as_of and ticker not in tickers:
                tickers.append(ticker)
                delisted_count += 1

        return UniverseSnapshot(
            as_of_date=as_of,
            tickers=tickers,
            delisted_included=delisted_count,
        )

    def check_survivorship_bias(
        self,
        training_tickers: list[str],
        training_start: date,
        training_end: date,
    ) -> dict:
        """Check if a training set suffers from survivorship bias."""
        start_universe = self.get_universe(training_start)
        end_universe = self.get_universe(training_end)

        if not start_universe.tickers:
            return {"check": "skipped", "reason": "no_historical_universe_data"}

        start_set = set(start_universe.tickers)
        training_set = set(training_tickers)

        # Tickers in start universe but missing from training = potential survivors-only bias
        missing = start_set - training_set
        delisted_missing = [t for t in missing if t in self._delisted]

        bias_score = len(delisted_missing) / max(len(start_set), 1)

        return {
            "check": "completed",
            "start_universe_size": len(start_set),
            "training_set_size": len(training_set),
            "delisted_missing": len(delisted_missing),
            "survivorship_bias_score": round(bias_score, 4),
            "is_biased": bias_score > 0.05,
        }
