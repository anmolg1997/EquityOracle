"""Redis cache adapter for scores, prices, and pre-computed data."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.logging import get_logger

log = get_logger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis(url: str = "redis://localhost:6379/0") -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(url, decode_responses=True)
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None


class RedisCache:
    """Typed wrapper around Redis for EquityOracle caching."""

    def __init__(self, redis: aioredis.Redis, prefix: str = "ep") -> None:
        self._redis = redis
        self._prefix = prefix

    def _key(self, namespace: str, key: str) -> str:
        return f"{self._prefix}:{namespace}:{key}"

    async def get_json(self, namespace: str, key: str) -> Any | None:
        raw = await self._redis.get(self._key(namespace, key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int = 86400,
    ) -> None:
        await self._redis.set(
            self._key(namespace, key),
            json.dumps(value, default=str),
            ex=ttl_seconds,
        )

    async def delete(self, namespace: str, key: str) -> None:
        await self._redis.delete(self._key(namespace, key))

    async def get_all_keys(self, namespace: str) -> list[str]:
        pattern = f"{self._prefix}:{namespace}:*"
        keys = []
        async for key in self._redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        return keys

    async def flush_namespace(self, namespace: str) -> int:
        keys = await self.get_all_keys(namespace)
        if keys:
            return await self._redis.delete(*keys)
        return 0

    async def health_check(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception:
            return False
