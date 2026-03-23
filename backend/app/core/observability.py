"""OpenTelemetry tracing, correlation IDs, and structured metrics."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.core.types import CorrelationId, new_correlation_id

_tracer: trace.Tracer | None = None
_metrics: dict[str, list[float]] = {}


def setup_tracing(service_name: str = "equityoracle") -> None:
    global _tracer
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is None:
        setup_tracing()
    assert _tracer is not None
    return _tracer


@contextmanager
def trace_span(
    name: str,
    correlation_id: CorrelationId | None = None,
    attributes: dict[str, Any] | None = None,
) -> Generator[trace.Span, None, None]:
    tracer = get_tracer()
    attrs = dict(attributes or {})
    if correlation_id:
        attrs["correlation_id"] = correlation_id
    with tracer.start_as_current_span(name, attributes=attrs) as span:
        yield span


def record_metric(name: str, value: float) -> None:
    _metrics.setdefault(name, []).append(value)


def get_metrics() -> dict[str, list[float]]:
    return dict(_metrics)


def create_pipeline_context() -> CorrelationId:
    return new_correlation_id()
