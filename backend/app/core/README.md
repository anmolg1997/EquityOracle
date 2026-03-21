# Core

Shared kernel used by all bounded contexts. Contains foundational types, cross-cutting concerns, and infrastructure-agnostic utilities.

## Files

| File | Purpose |
|------|---------|
| `types.py` | Value objects (`Ticker`, `Market`, `TimeHorizon`, `DateRange`), enums (`CircuitBreakerState`, `AutonomyLevel`), and pipeline context (`PipelineRunContext`, `CorrelationId`) |
| `events.py` | In-process async pub/sub `EventBus` for domain events. Subscribe with `bus.subscribe(EventType, handler)`, publish with `bus.publish(event)` |
| `exceptions.py` | Typed exception hierarchy rooted at `EquityOracleError`. Subclasses: `DataProviderError`, `ValidationError`, `InsufficientDataError`, `LookaheadBiasError`, `RiskLimitBreached` |
| `logging.py` | structlog configuration with correlation ID binding, JSON output for production |
| `observability.py` | OpenTelemetry tracing setup, span creation helpers |
| `scheduler.py` | APScheduler configuration for daily pipeline jobs |

## Design Notes

- `Ticker` is a frozen dataclass combining `symbol`, `exchange`, and `market` — it's the universal identifier throughout the system.
- `CorrelationId` is generated at the API boundary (middleware) and threaded through every layer for end-to-end request tracing.
- `PipelineRunContext` wraps a pipeline execution with its correlation ID, start time, and market context.
- All exceptions carry a `details` dict for structured error context beyond the message string.
