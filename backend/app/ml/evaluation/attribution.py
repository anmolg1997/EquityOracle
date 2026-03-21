"""Signal and feature importance attribution tracking."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FeatureAttribution:
    feature_name: str
    importance: float
    rank: int
    category: str = ""  # "technical", "fundamental", "alternative"


@dataclass
class AttributionReport:
    top_features: list[FeatureAttribution]
    category_weights: dict[str, float]


def compute_attribution(
    feature_importances: dict[str, float],
    top_k: int = 20,
) -> AttributionReport:
    """Analyze feature importance and group by category."""
    sorted_features = sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)

    top: list[FeatureAttribution] = []
    for rank, (name, importance) in enumerate(sorted_features[:top_k], 1):
        category = _categorize_feature(name)
        top.append(FeatureAttribution(
            feature_name=name,
            importance=round(importance, 6),
            rank=rank,
            category=category,
        ))

    # Aggregate by category
    cat_totals: dict[str, float] = {}
    total_importance = sum(v for v in feature_importances.values())
    for name, imp in feature_importances.items():
        cat = _categorize_feature(name)
        cat_totals[cat] = cat_totals.get(cat, 0) + imp

    cat_weights = {k: round(v / max(total_importance, 1e-10), 4) for k, v in cat_totals.items()}

    return AttributionReport(top_features=top, category_weights=cat_weights)


def _categorize_feature(name: str) -> str:
    technical_prefixes = [
        "rsi", "macd", "adx", "bb_", "atr", "sma_", "ema_", "volume_", "obv",
        "stoch", "williams", "cci", "mfi", "return_", "volatility", "gap",
        "close_position", "higher_", "lower_", "dist_from", "vol_ratio",
    ]
    fundamental_prefixes = [
        "pe_", "pb_", "ev_", "roe", "roce", "debt_", "revenue_", "profit_",
        "operating_", "dividend_", "eps", "book_", "promoter_", "earnings_",
    ]

    name_lower = name.lower()
    for prefix in technical_prefixes:
        if name_lower.startswith(prefix):
            return "technical"
    for prefix in fundamental_prefixes:
        if name_lower.startswith(prefix):
            return "fundamental"
    return "alternative"
