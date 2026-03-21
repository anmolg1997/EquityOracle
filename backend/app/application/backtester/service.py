"""Backtest service — walk-forward validation and strategy testing."""

from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


class BacktestService:
    """Orchestrates backtesting with VectorBT integration."""

    async def run_backtest(self, config: dict) -> dict:
        log.info("backtest_started", config=config)
        return {
            "status": "not_implemented",
            "message": "VectorBT backtest integration — use walk-forward validation from ML module",
        }
