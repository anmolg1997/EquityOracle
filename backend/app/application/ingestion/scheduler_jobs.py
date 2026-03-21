"""Registered APScheduler jobs for data ingestion."""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.types import Market

log = get_logger(__name__)


async def daily_ingestion_job(market: str = "india") -> None:
    """Scheduled job: daily data ingestion at market close + 1 hour.

    For India (NSE closes at 15:30 IST), runs at ~16:30 IST.
    """
    from app.application.ingestion.service import IngestionService
    from app.infrastructure.data_providers.factory import create_data_provider
    from app.infrastructure.persistence.database import async_session_factory
    from app.infrastructure.persistence.repositories.market_data_repo import SQLMarketDataRepository

    log.info("scheduled_ingestion_triggered", market=market)
    m = Market(market)
    provider = create_data_provider(m)

    async with async_session_factory() as session:
        repo = SQLMarketDataRepository(session)
        service = IngestionService(provider=provider, repository=repo)
        result = await service.run_daily_ingestion(market=m)
        log.info(
            "scheduled_ingestion_completed",
            tickers=result.tickers_processed,
            saved=result.records_saved,
            errors=len(result.errors),
        )
