# Infrastructure Layer

Concrete adapters implementing domain ports. All external I/O lives here.

## Structure

```
infrastructure/
├── data_providers/
│   ├── factory.py           Creates provider instances by market
│   ├── india.py             yfinance + nselib (OHLCV, fundamentals, insider deals, FII/DII)
│   ├── us.py                yfinance + Alpha Vantage
│   ├── global_screener.py   TradingView-Screener integration
│   └── resilience.py        ResilientDataProvider: fallback chain with health tracking
├── persistence/
│   ├── database.py          AsyncSession factory, engine setup
│   ├── models.py            SQLAlchemy 2.0 ORM models (248 lines)
│   └── repositories/        Concrete repositories (market_data, portfolio, recommendation, performance)
├── cache/
│   ├── redis.py             Redis wrapper (TTL-based caching, connection pooling)
│   └── precompute.py        Nightly batch pre-computation of composite scores
├── llm/
│   ├── base.py              Abstract LLM interface
│   ├── factory.py           Creates LLM client by config
│   ├── gemini.py            Google Gemini adapter via litellm
│   ├── ollama.py            Local Ollama adapter (free, no API key)
│   └── cost_tracker.py      Daily budget tracking, per-call recording, local LLM recommendation
├── sentiment/
│   ├── finbert.py           FinBERT transformer for headline sentiment (runs locally)
│   ├── news_api.py          NewsAPI headline fetcher
│   └── reddit.py            Reddit sentiment scraper
└── broker/
    ├── paper.py             Paper broker (fills at specified price, no real orders)
    ├── zerodha.py           Zerodha Kite API stub
    └── alpaca.py            Alpaca API stub
```

## Key Concepts

- **ResilientDataProvider** wraps multiple providers with automatic failover. Tracks per-provider health (consecutive failures, latency, last success).
- **LLM cost tracking** records every call (tokens in/out, cost, model). The daily budget prevents surprise cloud bills. When budget is exhausted, automatically switches to Ollama.
- **Pre-computation** runs nightly to populate Redis with composite scores. This gives the frontend sub-50ms response times instead of computing scores on-demand.
- **All persistence** uses SQLAlchemy 2.0 async sessions. The ORM models map to domain models via explicit conversion (no domain model inherits from Base).
