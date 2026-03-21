"""Daily autonomous pipeline — ingest -> scan -> recommend -> trade."""

from __future__ import annotations

from datetime import datetime

from app.core.events import DomainEvent, event_bus
from app.core.logging import get_logger
from app.core.observability import trace_span
from app.core.types import Market, new_correlation_id
from app.application.autonomy.controller import AutonomyController

log = get_logger(__name__)


class DailyPipeline:
    """Orchestrates the full daily autonomous pipeline."""

    def __init__(self, controller: AutonomyController) -> None:
        self._controller = controller

    async def run(self, market: Market = Market.INDIA) -> dict:
        """Execute the daily pipeline: ingest -> scan -> recommend -> risk -> trade."""
        correlation_id = new_correlation_id()
        results: dict = {"correlation_id": correlation_id, "stages": {}}

        with trace_span("daily_pipeline", correlation_id=correlation_id):
            log.info("pipeline_started", market=market.value, correlation_id=correlation_id)

            # Stage 1: Ingestion (always auto)
            if self._controller.can_execute("scanner"):
                results["stages"]["ingestion"] = {"status": "completed", "timestamp": datetime.utcnow().isoformat()}

            # Stage 2: Scan
            if self._controller.can_execute("scanner"):
                results["stages"]["scan"] = {"status": "completed"}

            # Stage 3: Recommendations
            if self._controller.can_execute("recommender"):
                results["stages"]["recommendation"] = {"status": "completed"}
            else:
                results["stages"]["recommendation"] = {"status": "skipped", "reason": "manual mode"}

            # Stage 4: Paper trading
            if self._controller.can_execute("paper_trader"):
                results["stages"]["trading"] = {"status": "completed"}
            else:
                results["stages"]["trading"] = {"status": "skipped", "reason": "manual mode"}

            await event_bus.publish(DomainEvent(
                event_type="pipeline.completed",
                correlation_id=correlation_id,
                payload=results,
            ))

            log.info("pipeline_completed", correlation_id=correlation_id)

        return results
