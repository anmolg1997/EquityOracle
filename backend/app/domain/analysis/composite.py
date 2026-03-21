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
    as_of: date | None = None,
) -> CompositeScore:
    """Compute the final composite score as a weighted aggregate of pillars."""
    w = weights or {
        "technical": 0.25,
        "fundamental": 0.25,
        "sentiment": 0.20,
        "ml_prediction": 0.30,
    }

    tech_val = float(technical.score) * w["technical"]
    fund_val = float(factor.composite) * w["fundamental"]
    sent_val = float(sentiment.composite * 100 if sentiment else Decimal(50)) * w["sentiment"]
    ml_val = float(ml_prediction) * w["ml_prediction"]

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
        weights_used=w,
        pillar_correlations=pillar_correlations or {},
    )
