# Architecture Overview

## The Big Picture

EquityOracle follows **Hexagonal Architecture** (Ports & Adapters) organized into **DDD Bounded Contexts**. If those terms are new to you, here's the plain version:

- **Domain logic** (the brains) lives in `domain/` folders and has **zero external dependencies** — no database calls, no HTTP requests, no file I/O. It only works with plain Python objects.
- **Infrastructure** (the plumbing) lives in `infrastructure/` and handles all the messy real-world stuff — talking to APIs, databases, caches.
- **Ports** are abstract interfaces (Python ABCs) that the domain defines. The domain says "I need a way to get stock prices" without caring _how_.
- **Adapters** are concrete implementations in infrastructure. Today it's yfinance; tomorrow it could be Bloomberg — the domain never changes.

This means you can test all business logic without a database, internet connection, or API key.

## Bounded Contexts

Each "context" is a self-contained area of the business:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Market Data   │────▶│    Analysis     │────▶│ Recommendation  │
│                 │     │                 │     │                 │
│ • OHLCV prices  │     │ • 50+ tech      │     │ • Multi-horizon │
│ • Fundamentals  │     │   indicators    │     │   signals       │
│ • Insider deals │     │ • Factor scores │     │ • Exit rules    │
│ • Inst. flows   │     │ • Composite     │     │ • LLM thesis    │
│ • Quality gates │     │   scoring       │     │ • Audit trail   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐              │
│      Risk       │◀────│    Portfolio    │◀─────────────┘
│                 │     │                 │
│ • Circuit       │     │ • Paper broker  │
│   breaker       │     │ • Slippage      │
│ • Regime detect │     │ • Transaction   │
│ • Position      │     │   costs         │
│   limits        │     │ • Tax model     │
└─────────────────┘     └─────────────────┘
```

Contexts communicate through:
1. **Direct function calls** within the same request (scanner calls analysis which calls market data)
2. **Domain events** via an async in-process EventBus for side effects (audit logging, cache invalidation, alerts)

## Layer Breakdown

### 1. Core (`app/core/`)

Shared kernel — things every context needs:
- `types.py` — Value objects: `Ticker`, `Market`, `TimeHorizon`, `CircuitBreakerState`
- `events.py` — In-process async pub/sub EventBus
- `exceptions.py` — Typed exception hierarchy (`DataProviderError → EquityOracleError`)
- `logging.py` — structlog with correlation IDs
- `observability.py` — OpenTelemetry tracing

### 2. Domain (`app/domain/`)

Pure business logic. No imports from `infrastructure/`. Each context has:
- `models.py` — Dataclasses representing domain concepts
- `ports.py` — Abstract interfaces for external capabilities
- Business logic modules (e.g., `quality.py`, `scoring.py`, `circuit_breaker.py`)

### 3. Application (`app/application/`)

Use case orchestration. Coordinates multiple domains to fulfill a user action:
- `scanner/` — Runs filter presets across the universe
- `recommender/` — Generates recommendations with debate and thesis
- `autonomy/` — Self-improvement pipeline, A/B testing
- `ingestion/` — Daily data fetch with provider resilience

### 4. Infrastructure (`app/infrastructure/`)

Concrete adapters implementing domain ports:
- `data_providers/` — yfinance, nselib, TradingView-Screener, with resilient fallback chain
- `persistence/` — PostgreSQL via SQLAlchemy 2.0 async
- `cache/` — Redis for pre-computed scores and session data
- `llm/` — litellm gateway with cost tracking and budget caps
- `sentiment/` — FinBERT (local), NewsAPI, Reddit
- `broker/` — Paper broker (production-ready), Zerodha/Alpaca stubs

### 5. API (`app/api/`)

FastAPI endpoints:
- `rest/` — Scanner, recommendations, portfolio, autonomy, health
- `sse/` — Server-Sent Events for streaming LLM debate and thesis generation
- `middleware.py` — Correlation ID injection, response timing

### 6. ML (`app/ml/`)

Machine learning pipeline with explicit safeguards:
- `features/` — Technical, fundamental, and alternative feature engineering
- `models/` — XGBoost classifier, LSTM, ensemble with confidence
- `safeguards/` — Point-in-time enforcement, survivorship bias checks, overfitting detection
- `training/` — Walk-forward validation, model registry
- `evaluation/` — Calibration checks, feature attribution

## Key Architectural Properties

| Property | How It's Achieved |
|----------|-------------------|
| **Testability** | Domain has zero I/O → 300 tests run in <1s without any infrastructure |
| **Swappability** | Ports/adapters → change data source without touching business logic |
| **Auditability** | Every recommendation has a `DecisionAudit` with full input context |
| **Resilience** | `ResilientDataProvider` wraps multiple sources in a fallback chain |
| **Safety** | Circuit breaker auto-pauses trading on drawdown or accuracy drops |
| **Observability** | Every request gets a correlation ID traced through all layers |
