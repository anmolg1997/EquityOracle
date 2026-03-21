"""Data provider resilience — health checks, fallback chains, staleness alerting."""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.core.logging import get_logger
from app.core.types import Market, Ticker
from app.domain.market_data.models import DataProviderHealth, OHLCV, FundamentalData
from app.domain.market_data.ports import MarketDataProvider
from app.core.exceptions import ProviderUnavailableError

log = get_logger(__name__)


class ResilientDataProvider(MarketDataProvider):
    """Wraps multiple providers in a fallback chain with health monitoring.

    Tries providers in order. If one fails, logs the failure, updates health
    state, and tries the next. If all fail, raises ProviderUnavailableError.
    """

    def __init__(self, providers: list[MarketDataProvider]) -> None:
        if not providers:
            raise ValueError("At least one provider is required")
        self._providers = providers
        self._health: dict[int, DataProviderHealth] = {}

    @property
    def provider_health(self) -> list[DataProviderHealth]:
        return list(self._health.values())

    async def get_ohlcv(self, ticker: Ticker, start, end) -> list[OHLCV]:
        return await self._with_fallback("get_ohlcv", ticker=ticker, start=start, end=end)

    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        return await self._with_fallback("get_fundamentals", ticker=ticker)

    async def get_insider_deals(self, ticker, days=30):
        return await self._with_fallback("get_insider_deals", ticker=ticker, days=days)

    async def get_institutional_flows(self, market, days=30):
        return await self._with_fallback("get_institutional_flows", market=market, days=days)

    async def get_market_breadth(self, market):
        return await self._with_fallback("get_market_breadth", market=market)

    async def get_universe(self, market: Market) -> list[Ticker]:
        return await self._with_fallback("get_universe", market=market)

    async def health_check(self) -> DataProviderHealth:
        results: list[DataProviderHealth] = []
        for i, provider in enumerate(self._providers):
            h = await provider.health_check()
            self._health[i] = h
            results.append(h)

        any_healthy = any(r.is_healthy for r in results)
        return DataProviderHealth(
            provider_name="resilient_chain",
            is_healthy=any_healthy,
            last_success=max(
                (r.last_success for r in results if r.last_success),
                default=None,
            ),
        )

    async def _with_fallback(self, method_name: str, **kwargs):
        errors: list[str] = []

        for i, provider in enumerate(self._providers):
            try:
                fn = getattr(provider, method_name)
                result = await fn(**kwargs)

                health = self._health.get(i)
                if health:
                    health.consecutive_failures = 0
                    health.is_healthy = True
                    health.last_success = datetime.utcnow()

                return result

            except Exception as e:
                provider_name = type(provider).__name__
                log.warning(
                    "provider_fallback",
                    provider=provider_name,
                    method=method_name,
                    error=str(e),
                    fallback_index=i + 1,
                )
                errors.append(f"{provider_name}: {e}")

                health = self._health.setdefault(
                    i,
                    DataProviderHealth(provider_name=provider_name),
                )
                health.consecutive_failures += 1
                health.is_healthy = False
                health.last_failure = datetime.utcnow()
                health.error_message = str(e)

        raise ProviderUnavailableError(
            f"All providers failed for {method_name}: {'; '.join(errors)}"
        )

    async def run_health_checks(self) -> list[DataProviderHealth]:
        tasks = [p.health_check() for p in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_list: list[DataProviderHealth] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                h = DataProviderHealth(
                    provider_name=type(self._providers[i]).__name__,
                    is_healthy=False,
                    error_message=str(result),
                )
            else:
                h = result
            self._health[i] = h
            health_list.append(h)

        return health_list
