"""VectorBT adapter for fast backtesting."""

from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)


class VectorBTAdapter:
    """Wrapper around VectorBT for strategy backtesting.

    Provides a clean interface for running vectorized backtests
    on EquityOracle strategies.
    """

    async def run(self, strategy_config: dict) -> dict:
        return {"status": "stub", "message": "VectorBT integration pending"}
