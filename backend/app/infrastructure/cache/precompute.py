"""Nightly batch pre-compute orchestrator — scores -> Redis for sub-100ms serving."""

from __future__ import annotations

from app.core.logging import get_logger
from app.infrastructure.cache.redis import RedisCache

log = get_logger(__name__)


class PrecomputeOrchestrator:
    """Runs after nightly ingestion to pre-compute all scores.

    Phases 2+ will add indicator/factor/composite computations.
    For now this serves as the scaffold that the daily pipeline calls.
    """

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    async def run(self, market: str = "india") -> dict[str, int]:
        """Execute the full pre-compute pipeline.

        Returns counts of items cached per category.
        """
        log.info("precompute_started", market=market)

        counts: dict[str, int] = {
            "technical_scores": 0,
            "factor_scores": 0,
            "composite_scores": 0,
        }

        # Phase 2 will populate these
        await self._cache.set_json("meta", f"precompute_status:{market}", {
            "status": "completed",
            "counts": counts,
        })

        log.info("precompute_completed", market=market, counts=counts)
        return counts
