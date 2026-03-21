"""FastAPI application factory with lifespan management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.middleware import CorrelationIdMiddleware
from app.api.rest.analysis import router as analysis_router
from app.api.rest.autonomy import router as autonomy_router
from app.api.rest.health import router as health_router
from app.api.rest.performance import router as performance_router
from app.api.rest.portfolio import router as portfolio_router
from app.api.rest.recommendations import router as recommendations_router
from app.api.rest.scanner import router as scanner_router
from app.api.rest.system import router as system_router
from app.api.sse.debate import router as debate_sse_router
from app.api.sse.thesis import router as thesis_sse_router
from app.config import settings
from app.core.logging import setup_logging
from app.core.observability import setup_tracing
from app.infrastructure.cache.redis import close_redis
from app.infrastructure.persistence.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    setup_tracing()
    await init_db()
    yield
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="EquityOracle",
        description="Global equity recommender with multi-horizon predictions",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Response-Time-Ms"],
    )

    app.include_router(health_router)
    app.include_router(analysis_router)
    app.include_router(autonomy_router)
    app.include_router(performance_router)
    app.include_router(portfolio_router)
    app.include_router(recommendations_router)
    app.include_router(scanner_router)
    app.include_router(system_router)
    app.include_router(debate_sse_router)
    app.include_router(thesis_sse_router)

    return app


app = create_app()
