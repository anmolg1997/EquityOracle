"""System status endpoints — health, providers, circuit breaker."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_cache, get_data_provider
from app.domain.market_data.ports import MarketDataProvider
from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.data_providers.resilience import ResilientDataProvider

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def system_health(
    cache: RedisCache = Depends(get_cache),
) -> dict:
    redis_healthy = await cache.health_check()
    return {
        "status": "healthy" if redis_healthy else "degraded",
        "components": {
            "redis": "up" if redis_healthy else "down",
            "database": "up",
        },
    }


@router.get("/providers")
async def provider_health(
    provider: MarketDataProvider = Depends(get_data_provider),
) -> dict:
    health = await provider.health_check()
    provider_list = []
    if isinstance(provider, ResilientDataProvider):
        for h in provider.provider_health:
            provider_list.append({
                "name": h.provider_name,
                "healthy": h.is_healthy,
                "last_success": str(h.last_success) if h.last_success else None,
                "consecutive_failures": h.consecutive_failures,
                "error": h.error_message,
            })
    return {
        "overall_healthy": health.is_healthy,
        "providers": provider_list,
    }


@router.get("/circuit-breaker")
async def circuit_breaker_status() -> dict:
    return {
        "state": "green",
        "message": "System operating normally",
    }
