"""Autonomy configuration REST API."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/autonomy", tags=["autonomy"])


@router.get("/config")
async def get_autonomy_config() -> dict:
    return {
        "engines": {
            "scanner": {"level": "full_auto", "can_execute": True},
            "recommender": {"level": "semi_auto", "can_execute": True},
            "paper_trader": {"level": "manual", "can_execute": False},
            "self_improvement": {"level": "semi_auto", "can_execute": True},
        },
        "circuit_breaker": "green",
    }
