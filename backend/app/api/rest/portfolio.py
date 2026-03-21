"""Portfolio REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio() -> dict:
    return {
        "portfolio_id": "default",
        "positions": [],
        "cash": 1_000_000,
        "total_value": 1_000_000,
        "message": "Paper trading portfolio — use POST endpoints to execute trades",
    }


@router.get("/positions")
async def get_positions() -> dict:
    return {"positions": [], "open_count": 0, "closed_count": 0}


@router.get("/performance")
async def get_performance() -> dict:
    return {
        "gross_return_pct": 0,
        "net_return_pct": 0,
        "total_trades": 0,
        "win_rate": 0,
        "total_costs": 0,
        "total_tax": 0,
    }
