"""APScheduler setup and job registry."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.logging import get_logger

log = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        log.info("scheduler_started")


async def shutdown_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler_stopped")
