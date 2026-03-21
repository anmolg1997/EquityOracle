"""FastAPI dependency injection — maps ports to adapters."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.types import Market
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository
from app.infrastructure.cache.redis import RedisCache, get_redis
from app.infrastructure.data_providers.factory import create_data_provider
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.repositories.market_data_repo import SQLMarketDataRepository


async def get_market_data_repository(
    session: AsyncSession = Depends(get_session),
) -> MarketDataRepository:
    return SQLMarketDataRepository(session)


async def get_data_provider(
    market: str = "india",
) -> MarketDataProvider:
    return create_data_provider(Market(market))


async def get_cache() -> AsyncGenerator[RedisCache, None]:
    redis = await get_redis(settings.redis.url)
    yield RedisCache(redis)
