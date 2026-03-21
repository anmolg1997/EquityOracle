# EquityOracle Wiki

Complete documentation for the EquityOracle equity recommender system.

## Reading Order

Start here if you're new. Each document builds on the previous one.

### Foundation
1. **[Getting Started](01-getting-started.md)** — Prerequisites, installation, first run
2. **[How It Works](02-how-it-works.md)** — End-to-end pipeline walkthrough (data in → recommendation out)
3. **[Architecture Overview](00-architecture-overview.md)** — Hexagonal architecture, bounded contexts, layer breakdown
4. **[Design Decisions](03-design-decisions.md)** — Why we chose each pattern and technology

### Domain Deep Dives
5. **[Market Data](04-market-data.md)** — Data sources, OHLCV, quality gates, liquidity scoring
6. **[Analysis Engine](05-analysis-engine.md)** — Technical indicators, factor model, decorrelation, composite scoring
7. **[Recommendation Engine](06-recommendation-engine.md)** — Signal generation, exit rules, LLM debate, audit trail
8. **[Portfolio Simulator](07-portfolio-simulator.md)** — Paper trading, transaction costs, slippage, tax, sizing strategies
9. **[Risk Management](08-risk-management.md)** — Circuit breaker, regime detection, pre-trade validation
10. **[ML Pipeline](09-ml-pipeline.md)** — Feature engineering, models, overfitting safeguards, walk-forward validation
11. **[Autonomy System](10-autonomy-system.md)** — Self-improvement, A/B testing, automation levels

### Operations
12. **[Frontend Guide](11-frontend-guide.md)** — UI architecture, pages, real-time features, dev setup
13. **[Testing Guide](12-testing-guide.md)** — 300 tests, structure, running, coverage

### Reference
14. **[Glossary](13-glossary.md)** — Finance + tech terms explained for developers

## Section READMEs

Each code directory has its own README with file-level documentation:

- [`backend/`](../backend/README.md) — Backend overview and setup
- [`frontend/`](../frontend/README.md) — Frontend overview and setup
- [`configs/`](../configs/README.md) — YAML configuration files
- [`backend/app/core/`](../backend/app/core/README.md) — Shared kernel
- [`backend/app/domain/market_data/`](../backend/app/domain/market_data/README.md) — Market data domain
- [`backend/app/domain/analysis/`](../backend/app/domain/analysis/README.md) — Analysis domain
- [`backend/app/domain/recommendation/`](../backend/app/domain/recommendation/README.md) — Recommendation domain
- [`backend/app/domain/portfolio/`](../backend/app/domain/portfolio/README.md) — Portfolio domain
- [`backend/app/domain/risk/`](../backend/app/domain/risk/README.md) — Risk domain
- [`backend/app/ml/`](../backend/app/ml/README.md) — ML pipeline
- [`backend/app/application/`](../backend/app/application/README.md) — Application layer
- [`backend/app/infrastructure/`](../backend/app/infrastructure/README.md) — Infrastructure adapters
- [`backend/app/api/`](../backend/app/api/README.md) — API endpoints
