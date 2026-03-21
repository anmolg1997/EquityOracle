"""Ingestion service — fetches data from providers, validates, and stores.

Orchestrates: Provider -> Quality Gate -> Repository, with resilience.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.core.events import DomainEvent, event_bus
from app.core.logging import get_logger
from app.core.observability import trace_span
from app.core.types import CorrelationId, Market, Ticker, new_correlation_id
from app.domain.market_data.liquidity import compute_liquidity_profile, passes_liquidity_filter
from app.domain.market_data.models import OHLCV
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository
from app.domain.market_data.quality import QualityReport, check_freshness, run_quality_gate

log = get_logger(__name__)


@dataclass
class IngestionResult:
    market: Market
    correlation_id: CorrelationId
    tickers_processed: int = 0
    records_saved: int = 0
    quality_flagged: int = 0
    liquidity_filtered: int = 0
    errors: list[str] = field(default_factory=list)


class IngestionService:
    """Orchestrates daily data ingestion with quality gates and liquidity filtering."""

    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository,
        min_liquidity_value: Decimal = Decimal("1_000_000"),
    ) -> None:
        self._provider = provider
        self._repo = repository
        self._min_liquidity = min_liquidity_value

    async def run_daily_ingestion(
        self,
        market: Market = Market.INDIA,
        lookback_days: int = 5,
        batch_size: int = 50,
    ) -> IngestionResult:
        """Run the full daily ingestion pipeline.

        1. Get universe from provider
        2. Fetch OHLCV for each ticker
        3. Run quality gate
        4. Compute and save liquidity profiles
        5. Save validated data
        """
        correlation_id = new_correlation_id()
        result = IngestionResult(market=market, correlation_id=correlation_id)

        with trace_span("daily_ingestion", correlation_id=correlation_id, attributes={"market": market.value}):
            log.info("ingestion_started", market=market.value, correlation_id=correlation_id)

            tickers = await self._provider.get_universe(market)
            log.info("universe_loaded", count=len(tickers))

            end = date.today()
            start = end - timedelta(days=lookback_days)

            for i in range(0, len(tickers), batch_size):
                batch = tickers[i : i + batch_size]
                await self._ingest_batch(batch, start, end, result)

            # Ingest institutional flows
            try:
                flows = await self._provider.get_institutional_flows(market)
                if flows:
                    await self._repo.save_institutional_flows(flows)
            except Exception as e:
                log.warning("flow_ingestion_failed", error=str(e))

            # Ingest breadth
            try:
                breadth = await self._provider.get_market_breadth(market)
                if breadth:
                    await self._repo.save_market_breadth(breadth)
            except Exception as e:
                log.warning("breadth_ingestion_failed", error=str(e))

            log.info(
                "ingestion_completed",
                tickers=result.tickers_processed,
                saved=result.records_saved,
                flagged=result.quality_flagged,
                filtered=result.liquidity_filtered,
                errors=len(result.errors),
            )

            await event_bus.publish(DomainEvent(
                event_type="ingestion.completed",
                correlation_id=correlation_id,
                payload={
                    "market": market.value,
                    "tickers_processed": result.tickers_processed,
                    "records_saved": result.records_saved,
                },
            ))

        return result

    async def _ingest_batch(
        self,
        tickers: list[Ticker],
        start: date,
        end: date,
        result: IngestionResult,
    ) -> None:
        tasks = [self._ingest_ticker(t, start, end) for t in tickers]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        for i, outcome in enumerate(outcomes):
            result.tickers_processed += 1
            if isinstance(outcome, Exception):
                result.errors.append(f"{tickers[i]}: {outcome}")
                continue

            records, quality_report, liquidity_ok = outcome
            if not records:
                continue

            if not liquidity_ok:
                result.liquidity_filtered += 1

            result.quality_flagged += quality_report.flagged
            valid_records = [r for r in records if r.data_quality.value == "ok"]
            if valid_records:
                saved = await self._repo.save_ohlcv_batch(valid_records)
                result.records_saved += saved

    async def _ingest_ticker(
        self,
        ticker: Ticker,
        start: date,
        end: date,
    ) -> tuple[list[OHLCV], QualityReport, bool]:
        records = await self._provider.get_ohlcv(ticker, start, end)

        quality_report = run_quality_gate(records)

        profile = compute_liquidity_profile(ticker, records)
        await self._repo.save_liquidity_profile(profile)
        liquidity_ok = passes_liquidity_filter(profile, self._min_liquidity)

        return records, quality_report, liquidity_ok

    async def backfill_historical(
        self,
        tickers: list[Ticker],
        start: date,
        end: date,
    ) -> IngestionResult:
        """Backfill historical data for a list of tickers."""
        correlation_id = new_correlation_id()
        result = IngestionResult(market=Market.INDIA, correlation_id=correlation_id)

        log.info("backfill_started", tickers=len(tickers), start=str(start), end=str(end))

        for ticker in tickers:
            try:
                records = await self._provider.get_ohlcv(ticker, start, end)
                if records:
                    saved = await self._repo.save_ohlcv_batch(records)
                    result.records_saved += saved
                result.tickers_processed += 1
            except Exception as e:
                result.errors.append(f"{ticker}: {e}")
                log.error("backfill_ticker_failed", ticker=str(ticker), error=str(e))

        log.info("backfill_completed", saved=result.records_saved)
        return result
