"""Pure domain models for the Analysis bounded context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.core.types import Ticker


@dataclass
class TechnicalScore:
    ticker: Ticker
    as_of_date: date
    rsi_14: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_histogram: Decimal | None = None
    adx_14: Decimal | None = None
    bb_position: Decimal | None = None  # 0=lower, 0.5=mid, 1=upper
    sma_20: Decimal | None = None
    sma_50: Decimal | None = None
    sma_150: Decimal | None = None
    sma_200: Decimal | None = None
    ema_12: Decimal | None = None
    ema_26: Decimal | None = None
    atr_14: Decimal | None = None
    volume_ratio: Decimal | None = None
    obv_trend: str = ""  # "up", "down", "flat"
    rs_rating: Decimal | None = None  # relative strength 0-99
    score: Decimal = Decimal(0)  # composite technical score 0-100

    @property
    def is_bullish(self) -> bool:
        return self.score >= Decimal(60)


@dataclass
class FactorScore:
    ticker: Ticker
    as_of_date: date
    momentum_score: Decimal = Decimal(0)  # 0-100
    quality_score: Decimal = Decimal(0)
    value_score: Decimal = Decimal(0)
    composite: Decimal = Decimal(0)

    momentum_details: dict = field(default_factory=dict)
    quality_details: dict = field(default_factory=dict)
    value_details: dict = field(default_factory=dict)


@dataclass
class SentimentScore:
    ticker: Ticker
    as_of_date: date
    news_score: Decimal = Decimal(0)  # -1 to 1
    social_score: Decimal = Decimal(0)
    insider_score: Decimal = Decimal(0)
    institutional_flow_score: Decimal = Decimal(0)
    composite: Decimal = Decimal(0)
    article_count: int = 0


@dataclass
class CompositeScore:
    ticker: Ticker
    as_of_date: date
    technical: Decimal = Decimal(0)
    fundamental: Decimal = Decimal(0)
    sentiment: Decimal = Decimal(0)
    ml_prediction: Decimal = Decimal(0)
    overall: Decimal = Decimal(0)
    effective_signal_count: Decimal = Decimal(0)

    weights_used: dict[str, float] = field(default_factory=dict)
    pillar_correlations: dict[str, float] = field(default_factory=dict)

    @property
    def confidence_level(self) -> str:
        if self.overall >= Decimal(80):
            return "high"
        if self.overall >= Decimal(60):
            return "medium"
        return "low"


@dataclass
class ScanResult:
    ticker: Ticker
    composite_score: CompositeScore
    technical_score: TechnicalScore
    factor_score: FactorScore
    sentiment_score: SentimentScore | None = None
    passed_presets: list[str] = field(default_factory=list)
    rank: int = 0
