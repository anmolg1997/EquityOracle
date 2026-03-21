"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "equityoracle",
        "version": "0.1.0",
    }
