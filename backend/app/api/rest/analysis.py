"""Analysis REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_data_provider, get_market_data_repository
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/{ticker}")
async def get_analysis(
    ticker: str,
    repository: MarketDataRepository = Depends(get_market_data_repository),
) -> dict:
    return {
        "ticker": ticker,
        "technical_score": None,
        "factor_score": None,
        "sentiment_score": None,
        "message": "Use the scanner to populate analysis data",
    }
