"""Fundamental ratio-based features."""

from __future__ import annotations

import pandas as pd

from app.domain.market_data.models import FundamentalData


def compute_fundamental_features(
    fundamentals: FundamentalData | None,
    n_rows: int,
) -> pd.DataFrame:
    """Expand fundamental data into a feature DataFrame aligned with technical features."""
    features = pd.DataFrame(index=range(n_rows))

    if fundamentals is None:
        for col in _FUNDAMENTAL_COLUMNS:
            features[col] = float("nan")
        return features

    features["pe_ratio"] = _to_float(fundamentals.pe_ratio)
    features["pb_ratio"] = _to_float(fundamentals.pb_ratio)
    features["ev_ebitda"] = _to_float(fundamentals.ev_ebitda)
    features["roe"] = _to_float(fundamentals.roe)
    features["roce"] = _to_float(fundamentals.roce)
    features["debt_to_equity"] = _to_float(fundamentals.debt_to_equity)
    features["revenue_growth_3yr"] = _to_float(fundamentals.revenue_growth_3yr)
    features["profit_growth_3yr"] = _to_float(fundamentals.profit_growth_3yr)
    features["operating_margin"] = _to_float(fundamentals.operating_profit_margin)
    features["dividend_yield"] = _to_float(fundamentals.dividend_yield)
    features["eps"] = _to_float(fundamentals.eps)
    features["book_value"] = _to_float(fundamentals.book_value)
    features["promoter_holding"] = _to_float(fundamentals.promoter_holding_pct)

    # Derived
    pe = _to_float(fundamentals.pe_ratio)
    features["earnings_yield"] = 1.0 / pe if pe and pe > 0 else float("nan")

    return features


_FUNDAMENTAL_COLUMNS = [
    "pe_ratio", "pb_ratio", "ev_ebitda", "roe", "roce",
    "debt_to_equity", "revenue_growth_3yr", "profit_growth_3yr",
    "operating_margin", "dividend_yield", "eps", "book_value",
    "promoter_holding", "earnings_yield",
]


def _to_float(val) -> float | None:
    if val is None:
        return float("nan")
    return float(val)
