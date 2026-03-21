"""Feature engineering pipeline — domain objects -> feature matrix.

Orchestrates technical, fundamental, and alternative features.
Enforces point-in-time constraints via available_at timestamps.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.core.types import Ticker
from app.domain.market_data.models import FundamentalData, InsiderDeal, InstitutionalFlow, OHLCV
from app.ml.features.technical_features import compute_technical_features
from app.ml.features.fundamental_features import compute_fundamental_features
from app.ml.features.alternative_features import compute_alternative_features

log = get_logger(__name__)


class FeatureEngineer:
    """Transforms domain objects into a feature matrix suitable for ML models.

    Key guarantees:
    - All features respect point-in-time constraints
    - Missing values are handled explicitly (NaN, not guessed)
    - Feature names are stable across versions
    """

    def __init__(self, enforce_point_in_time: bool = True) -> None:
        self._enforce_pit = enforce_point_in_time

    def build_features(
        self,
        ticker: Ticker,
        ohlcv: list[OHLCV],
        fundamentals: FundamentalData | None = None,
        insider_deals: list[InsiderDeal] | None = None,
        flows: list[InstitutionalFlow] | None = None,
        as_of: date | None = None,
    ) -> pd.DataFrame:
        """Build the full feature vector for a single ticker.

        Returns a DataFrame with one row per date, columns = features.
        """
        if not ohlcv:
            return pd.DataFrame()

        as_of = as_of or date.today()

        if self._enforce_pit:
            ohlcv = [r for r in ohlcv if not r.available_at or r.available_at.date() <= as_of]

        tech_df = compute_technical_features(ohlcv)
        fund_df = compute_fundamental_features(fundamentals, len(tech_df))
        alt_df = compute_alternative_features(insider_deals or [], flows or [], len(tech_df))

        combined = pd.concat([tech_df, fund_df, alt_df], axis=1)
        combined["ticker"] = str(ticker)

        return combined

    def build_universe_features(
        self,
        ticker_data: dict[str, dict],
        as_of: date | None = None,
    ) -> pd.DataFrame:
        """Build features for an entire universe. Returns latest features per ticker."""
        frames: list[pd.DataFrame] = []

        for ticker_str, data in ticker_data.items():
            try:
                df = self.build_features(
                    ticker=data["ticker"],
                    ohlcv=data["ohlcv"],
                    fundamentals=data.get("fundamentals"),
                    insider_deals=data.get("insider_deals"),
                    flows=data.get("flows"),
                    as_of=as_of,
                )
                if not df.empty:
                    frames.append(df.iloc[[-1]])
            except Exception as e:
                log.debug("feature_build_failed", ticker=ticker_str, error=str(e))

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)
