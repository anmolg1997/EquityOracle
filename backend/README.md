# Backend

FastAPI application implementing the EquityOracle analysis and trading engine.

## Structure

```
app/
├── core/            Shared kernel: events, types, logging, observability
├── domain/          Pure business logic (zero external dependencies)
│   ├── market_data/     OHLCV models, quality gates, liquidity scoring
│   ├── analysis/        Technical indicators, factor scores, composite
│   ├── recommendation/  Signal generation, exit rules, thesis
│   ├── portfolio/       Paper trading engine, costs, sizing
│   └── risk/            Circuit breaker, regime detection, risk manager
├── ml/              ML pipeline with safeguards
│   ├── features/        Feature engineering (technical, fundamental, alternative)
│   ├── models/          XGBoost, LSTM, ensemble
│   ├── safeguards/      Point-in-time, survivorship bias, overfitting detection
│   ├── training/        Walk-forward validation
│   └── evaluation/      Calibration, attribution
├── application/     Use case orchestration
│   ├── scanner/         Stock screener with configurable presets
│   ├── recommender/     Recommendation generation with LLM debate
│   ├── autonomy/        Self-improvement, A/B testing, daily pipeline
│   ├── ingestion/       Data fetch with provider fallback
│   ├── backtester/      Historical strategy testing
│   └── simulator/       Event-driven simulation loop
├── infrastructure/  External adapters (DB, APIs, cache, LLM)
│   ├── data_providers/  yfinance, nselib, TradingView, Alpha Vantage
│   ├── persistence/     PostgreSQL + SQLAlchemy async
│   ├── cache/           Redis caching + precompute
│   ├── llm/             litellm gateway, cost tracker, Gemini/Ollama
│   ├── sentiment/       FinBERT, NewsAPI, Reddit
│   └── broker/          Paper broker, Zerodha/Alpaca stubs
├── api/             FastAPI endpoints
│   ├── rest/            Scanner, recommendations, portfolio, health
│   ├── sse/             Streaming debate + thesis generation
│   └── ws/              WebSocket for live portfolio updates
└── main.py          Application entry point
```

## Running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Testing

```bash
pytest tests/ -v                          # All 300 tests
pytest tests/ --cov=app --cov-report=html # Coverage report
```

## Key Dependencies

- **FastAPI** + **Pydantic v2** — API + validation
- **SQLAlchemy 2.0** (async) — Database ORM
- **pandas** + **pandas-ta** — Data manipulation + technical indicators
- **scikit-learn** + **xgboost** + **torch** — ML models
- **litellm** — LLM gateway
- **structlog** — Structured logging
- **opentelemetry** — Distributed tracing
