"""Weighted composite scoring logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.types import Ticker
from app.domain.analysis.models import CompositeScore, FactorScore, SentimentScore, TechnicalScore


def compute_composite(
    ticker: Ticker,
    technical: TechnicalScore,
    factor: FactorScore,
    sentiment: SentimentScore | None = None,
    ml_prediction: Decimal = Decimal(0),
    weights: dict[str, float] | None = None,
    effective_signal_count: Decimal = Decimal(0),
    pillar_correlations: dict[str, float] | None = None,
    adaptive_missing_pillars: bool = False,
    sentiment_available: bool = True,
    ml_available: bool = True,
    as_of: date | None = None,
) -> CompositeScore:
    """Compute the final composite score as a weighted aggregate of pillars."""
    w = weights or {
        "technical": 0.25,
        "fundamental": 0.25,
        "sentiment": 0.20,
        "ml_prediction": 0.30,
    }

    sentiment_score = float(sentiment.composite * 100 if sentiment else Decimal(50))
    ml_score = float(ml_prediction)

    effective_weights = dict(w)
    if adaptive_missing_pillars:
        active_pillars = ["technical", "fundamental"]
        if sentiment_available and sentiment is not None:
            active_pillars.append("sentiment")
        if ml_available:
            active_pillars.append("ml_prediction")

        total_weight = sum(w[p] for p in active_pillars)
        if total_weight > 0:
            effective_weights = {
                "technical": (w["technical"] / total_weight) if "technical" in active_pillars else 0.0,
                "fundamental": (w["fundamental"] / total_weight) if "fundamental" in active_pillars else 0.0,
                "sentiment": (w["sentiment"] / total_weight) if "sentiment" in active_pillars else 0.0,
                "ml_prediction": (w["ml_prediction"] / total_weight) if "ml_prediction" in active_pillars else 0.0,
            }

    tech_val = float(technical.score) * effective_weights["technical"]
    fund_val = float(factor.composite) * effective_weights["fundamental"]
    sent_val = sentiment_score * effective_weights["sentiment"]
    ml_val = ml_score * effective_weights["ml_prediction"]

    overall = Decimal(str(round(tech_val + fund_val + sent_val + ml_val, 2)))

    return CompositeScore(
        ticker=ticker,
        as_of_date=as_of or date.today(),
        technical=technical.score,
        fundamental=factor.composite,
        sentiment=sentiment.composite if sentiment else Decimal(0),
        ml_prediction=ml_prediction,
        overall=overall,
        effective_signal_count=effective_signal_count,
        weights_used=effective_weights,
        pillar_correlations=pillar_correlations or {},
    )
