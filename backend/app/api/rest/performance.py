"""Performance and accuracy REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/accuracy")
async def get_accuracy() -> dict:
    return {
        "overall_accuracy": None,
        "by_horizon": {},
        "by_confidence": {},
        "message": "Accuracy tracking populates as recommendations are verified",
    }


@router.get("/attribution")
async def get_attribution() -> dict:
    return {
        "pillar_contributions": {
            "technical": 0.25,
            "fundamental": 0.25,
            "sentiment": 0.20,
            "ml_prediction": 0.30,
        },
        "top_features": [],
    }
