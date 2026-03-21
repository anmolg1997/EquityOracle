# EquityOracle

A self-improving equity recommender that scans global markets, scores stocks across multiple dimensions, generates multi-horizon buy/sell signals with confidence scores, and manages a simulated portfolio with realistic costs — all running autonomously with built-in safeguards.

## What It Does

1. **Scans** — Pulls daily OHLCV, fundamentals, insider deals, and institutional flows from multiple data sources. Runs configurable screener presets (Minervini trend template, CANSLIM, momentum breakout, deep value).

2. **Analyzes** — Computes 50+ technical indicators, momentum/quality/value factor scores, FinBERT news sentiment, and ML-based return predictions. Combines everything into a weighted composite score with decorrelation checks.

3. **Recommends** — Generates BUY/SELL/HOLD signals across 5 time horizons (1 day → 3 months) with calibrated confidence. For top picks, runs a Bull/Bear LLM debate and generates an investment thesis.

4. **Simulates** — Executes recommendations in a paper portfolio with India-specific transaction costs (STT, stamp duty, GST), volume-aware slippage, and capital gains tax modelling (STCG 20%, LTCG 12.5% above ₹1.25L).

5. **Protects** — A four-level circuit breaker (GREEN → AMBER → RED → BLACK) monitors accuracy and drawdown, automatically reducing position sizes or pausing trading when performance degrades.

6. **Self-Improves** — Bayesian weight adjustment tunes composite scoring weights based on actual outcomes, validated through shadow A/B testing before deployment.

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                     │
│  Command Center │ Scanner │ Recommendations │ Portfolio      │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST + SSE
┌───────────────────────┴─────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Market   │ │ Analysis │ │ Recommend│ │ Portfolio│       │
│  │ Data     │ │ Domain   │ │ Domain   │ │ Domain   │       │
│  │ Domain   │ │          │ │          │ │          │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       │ Ports       │            │            │             │
│  ┌────┴─────────────┴────────────┴────────────┴─────┐       │
│  │              Infrastructure Layer                 │       │
│  │  yfinance │ nselib │ FinBERT │ Redis │ Postgres  │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Pattern:** Hexagonal Architecture (Ports & Adapters) with DDD Bounded Contexts. Domain logic has zero external dependencies — all I/O goes through abstract ports.

## Quick Start

```bash
# Clone and enter
git clone https://github.com/anmolg1997/EquityOracle.git
cd EquityOracle

# Option A: Docker (recommended)
cp .env.example .env
docker compose up -d

# Option B: Local development
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/                    # 300 tests, <1s

cd ../frontend && npm install
npm run dev                      # http://localhost:5173
```

See [wiki/01-getting-started.md](wiki/01-getting-started.md) for detailed setup.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 + TimescaleDB (time-series), Redis 7 (cache + pub/sub) |
| ML | XGBoost, PyTorch (LSTM), scikit-learn, FinBERT (local sentiment) |
| LLM | litellm gateway → Gemini / Ollama / Claude (with daily budget cap) |
| Data Sources | yfinance, nselib, TradingView-Screener, NewsAPI, Alpha Vantage |
| Frontend | React 18, TypeScript 5, Vite 6, Tailwind CSS, TradingView Charts |
| Infra | Docker Compose, OpenTelemetry, structlog |

## Market Support

| Market | Data Source | Transaction Costs | Status |
|--------|-----------|-------------------|--------|
| India (NSE/BSE) | yfinance + nselib | STT, stamp duty, GST, SEBI fee | Primary |
| US (NYSE/NASDAQ) | yfinance + Alpha Vantage | SEC fee, TAF, brokerage | Adapter ready |
| Global | TradingView-Screener | Configurable | Adapter ready |

## Project Structure

```
EquityOracle/
├── backend/
│   ├── app/
│   │   ├── core/           # Events, logging, types, observability
│   │   ├── domain/         # Pure business logic (zero I/O)
│   │   │   ├── market_data/    # OHLCV, quality gates, liquidity
│   │   │   ├── analysis/       # Technical, factors, composite scoring
│   │   │   ├── recommendation/ # Signals, exit rules, thesis
│   │   │   ├── portfolio/      # Engine, costs, sizing
│   │   │   └── risk/           # Circuit breaker, regime, drawdown
│   │   ├── ml/             # Feature engineering, models, safeguards
│   │   ├── application/    # Use cases (scanner, recommender, autonomy)
│   │   ├── infrastructure/ # Adapters (DB, APIs, cache, LLM)
│   │   └── api/            # REST + SSE endpoints, middleware
│   └── tests/              # 300 tests (unit + integration)
├── frontend/src/
│   ├── features/           # Page-level components
│   └── shared/             # API client, hooks, stores
├── configs/                # YAML: markets, risk, scanners, weights
├── wiki/                   # Full documentation
└── docker-compose.yml
```

## Documentation

Start here, in order:

| Doc | What You'll Learn |
|-----|-------------------|
| [Getting Started](wiki/01-getting-started.md) | Prerequisites, setup, first run |
| [How It Works](wiki/02-how-it-works.md) | End-to-end flow: data in → recommendation out |
| [Architecture Overview](wiki/00-architecture-overview.md) | Hexagonal architecture, bounded contexts, event bus |
| [Design Decisions](wiki/03-design-decisions.md) | Why we chose each pattern and technology |
| [Market Data](wiki/04-market-data.md) | Data sources, quality gates, liquidity scoring |
| [Analysis Engine](wiki/05-analysis-engine.md) | Technical indicators, factor model, composite scoring |
| [Recommendation Engine](wiki/06-recommendation-engine.md) | Signal generation, exit rules, LLM debate |
| [Portfolio Simulator](wiki/07-portfolio-simulator.md) | Paper trading, realistic costs, position sizing |
| [Risk Management](wiki/08-risk-management.md) | Circuit breaker, regime detection, position limits |
| [ML Pipeline](wiki/09-ml-pipeline.md) | Features, models, overfitting safeguards |
| [Autonomy System](wiki/10-autonomy-system.md) | Self-improvement, A/B testing, automation levels |
| [Frontend Guide](wiki/11-frontend-guide.md) | UI architecture, pages, real-time updates |
| [Testing Guide](wiki/12-testing-guide.md) | Test structure, running tests, coverage |
| [Glossary](wiki/13-glossary.md) | Finance + tech terms explained for developers |

## Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v                          # All 300 tests
pytest tests/unit/domain/ -v              # Domain logic only (103 tests)
pytest tests/integration/ -v              # Cross-domain flows (20 tests)
pytest tests/ --cov=app --cov-report=html # Coverage report
```

## License

MIT

## Author

[Anmol Jaiswal](https://github.com/anmolg1997)
