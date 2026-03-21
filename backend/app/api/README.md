# API Layer

FastAPI endpoints exposing EquityOracle functionality over HTTP.

## Structure

```
api/
├── rest/
│   ├── health.py            GET /health — service status
│   ├── scanner.py           POST /api/scanner/scan — run a filter preset
│   ├── recommendations.py   GET /api/recommendations — signal feed with filters
│   ├── analysis.py          GET /api/analysis/{ticker} — composite score breakdown
│   ├── portfolio.py         GET /api/portfolio, POST /api/portfolio/buy, /sell
│   ├── performance.py       GET /api/performance — equity curve, metrics
│   ├── autonomy.py          GET/PUT /api/autonomy/config — autonomy level management
│   └── system.py            GET /api/system/providers — data provider health
├── sse/
│   ├── debate.py            GET /api/debate/{ticker} — streamed Bull/Bear debate
│   └── thesis.py            GET /api/thesis/{ticker} — streamed investment thesis
├── ws/
│   └── __init__.py          WebSocket for live portfolio/circuit breaker updates
├── dependencies.py          FastAPI Depends() providers (DB session, services)
└── middleware.py             CorrelationIdMiddleware (injects X-Correlation-Id + X-Response-Time)
```

## Key Concepts

- **REST** for request-response operations (scan, fetch recommendations, place paper trades).
- **SSE** for streaming LLM text generation (debate and thesis). The frontend renders tokens as they arrive.
- **WebSocket** for bidirectional live updates (portfolio value changes, circuit breaker transitions).
- **Middleware** injects a `CorrelationId` into every request for end-to-end tracing. Also measures and adds `X-Response-Time` header.
- **Dependencies** use FastAPI's `Depends()` for dependency injection — database sessions, service instances, and authentication are injected declaratively.
