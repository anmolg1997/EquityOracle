"""Port interfaces for the Recommendation bounded context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.core.types import Ticker, TimeHorizon


class MLPredictor(ABC):
    """Port: generate return predictions with confidence."""

    @abstractmethod
    async def predict(
        self,
        ticker: Ticker,
        features: dict,
        horizons: list[TimeHorizon],
    ) -> list[dict]:
        ...


class ThesisGenerator(ABC):
    """Port: generate investment thesis via LLM."""

    @abstractmethod
    async def generate_thesis(self, ticker: Ticker, context: dict) -> str:
        ...

    @abstractmethod
    async def stream_thesis(self, ticker: Ticker, context: dict) -> AsyncIterator[str]:
        ...
