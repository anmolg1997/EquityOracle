"""Port interfaces for the Analysis bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.core.types import Ticker
from app.domain.analysis.models import SentimentScore, TechnicalScore
from app.domain.market_data.models import OHLCV


class TechnicalAnalyzer(ABC):
    """Port: compute technical indicators from OHLCV data."""

    @abstractmethod
    async def compute(self, ticker: Ticker, ohlcv: list[OHLCV]) -> TechnicalScore:
        ...


class SentimentAnalyzer(ABC):
    """Port: compute sentiment scores for a stock."""

    @abstractmethod
    async def analyze(self, ticker: Ticker, as_of: date) -> SentimentScore:
        ...
