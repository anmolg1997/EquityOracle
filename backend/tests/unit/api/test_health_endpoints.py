"""Tests for health and system API endpoints using FastAPI TestClient."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.api.rest.health import router as health_router
from app.api.rest.portfolio import router as portfolio_router
from app.api.rest.autonomy import router as autonomy_router


def _create_test_app() -> FastAPI:
    """Minimal app with only the dependency-free routers."""
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(portfolio_router)
    app.include_router(autonomy_router)
    return app


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_health_has_status_field(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "equityoracle"
        assert "version" in data


class TestPortfolioEndpoints:
    @pytest.mark.asyncio
    async def test_get_portfolio(self, client):
        resp = await client.get("/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert "cash" in data
        assert data["cash"] == 1_000_000

    @pytest.mark.asyncio
    async def test_get_positions(self, client):
        resp = await client.get("/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["positions"] == []
        assert data["open_count"] == 0

    @pytest.mark.asyncio
    async def test_get_performance(self, client):
        resp = await client.get("/portfolio/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "gross_return_pct" in data
        assert "win_rate" in data
        assert "total_costs" in data


class TestAutonomyEndpoint:
    @pytest.mark.asyncio
    async def test_get_autonomy_config(self, client):
        resp = await client.get("/autonomy/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "engines" in data
        assert "scanner" in data["engines"]
        assert data["engines"]["scanner"]["level"] == "full_auto"
        assert data["circuit_breaker"] == "green"

    @pytest.mark.asyncio
    async def test_autonomy_engine_states(self, client):
        resp = await client.get("/autonomy/config")
        data = resp.json()
        engines = data["engines"]
        assert engines["paper_trader"]["can_execute"] is False
        assert engines["recommender"]["can_execute"] is True
