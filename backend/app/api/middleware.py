"""Request middleware — correlation ID injection, timing, compression."""

from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.types import new_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Injects a correlation ID into every request and binds it to structlog context."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", new_correlation_id())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        structlog.contextvars.unbind_contextvars("correlation_id")
        return response
