"""Tests for API middleware — correlation ID injection, timing headers."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.api.middleware import CorrelationIdMiddleware
from app.api.rest.health import router as health_router


def _create_app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(health_router)
    return app


@pytest.fixture
def app():
    return _create_app_with_middleware()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestCorrelationIdMiddleware:
    @pytest.mark.asyncio
    async def test_generates_correlation_id(self, client):
        resp = await client.get("/health")
        assert "x-correlation-id" in resp.headers

    @pytest.mark.asyncio
    async def test_uses_provided_correlation_id(self, client):
        resp = await client.get("/health", headers={"X-Correlation-ID": "test-123"})
        assert resp.headers["x-correlation-id"] == "test-123"

    @pytest.mark.asyncio
    async def test_response_time_header(self, client):
        resp = await client.get("/health")
        assert "x-response-time-ms" in resp.headers
        time_ms = float(resp.headers["x-response-time-ms"])
        assert time_ms >= 0
