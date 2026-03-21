"""Recommendations REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_data_provider, get_market_data_repository
from app.application.recommender.service import RecommenderService
from app.core.types import Market, TimeHorizon
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
async def get_recommendations(
    market: str = Query(default="india"),
    horizon: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    repository: MarketDataRepository = Depends(get_market_data_repository),
    provider: MarketDataProvider = Depends(get_data_provider),
) -> dict:
    service = RecommenderService(provider=provider, repository=repository)

    horizons = None
    if horizon:
        horizons = [TimeHorizon(horizon)]

    recs = await service.generate_recommendations(
        market=Market(market),
        horizons=horizons,
        limit=limit,
    )

    return {
        "count": len(recs),
        "market": market,
        "recommendations": [
            {
                "ticker": str(r.signal.ticker),
                "direction": r.signal.direction.value,
                "horizon": r.signal.horizon.value,
                "strength": float(r.signal.strength),
                "expected_return_pct": float(r.signal.expected_return_pct),
                "confidence": float(r.signal.confidence),
                "independent_signals": float(r.signal.independent_signal_count),
                "exit_rules": [
                    {"type": er.exit_type.value, "description": er.description}
                    for er in r.exit_rules
                ],
            }
            for r in recs
        ],
    }
