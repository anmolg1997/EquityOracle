# Design Decisions

This document explains _why_ we chose each pattern and technology. For each decision, we note the alternatives considered and why we went the way we did.

## Architecture: Hexagonal + DDD

**Decision:** Hexagonal Architecture (Ports & Adapters) with Domain-Driven Design bounded contexts.

**Why not a simple MVC?** The system has complex business rules (tax calculations, circuit breaker state machines, ML safeguards) that need to be testable without infrastructure. In MVC, business logic often leaks into controllers or gets tangled with database queries. Hexagonal keeps domain pure.

**Why not microservices?** For a personal-first tool, microservices add deployment complexity without meaningful benefit. Bounded contexts give us the same logical separation — if we need to split later, each context already has clean boundaries.

**Trade-off:** More files and abstractions upfront. Worth it because 300 tests run in <1 second without any infrastructure.

## Database: PostgreSQL + TimescaleDB

**Decision:** PostgreSQL 16 with TimescaleDB extension for time-series data.

**Why not InfluxDB or pure time-series DB?** We need both relational data (portfolios, recommendations, audit trails) and time-series data (OHLCV). Running two separate databases adds operational complexity. TimescaleDB gives us time-series optimizations (automatic partitioning, compression) inside PostgreSQL.

**Why not SQLite?** Works for development but doesn't support async well, lacks time-series extensions, and would need migration for production.

## Cache: Redis

**Decision:** Redis 7 for caching pre-computed scores and as a lightweight pub/sub.

**Why pre-compute?** Computing composite scores for 500 stocks involves technical indicators, factor scores, ML predictions, and decorrelation — expensive in aggregate. Nightly batch pre-computation to Redis gives the frontend sub-50ms response times.

**Why not just HTTP caching?** The scores depend on complex domain logic, not just API responses. Redis lets us cache at the domain level.

## ML Models: XGBoost + LSTM Ensemble

**Decision:** XGBoost for tabular features, LSTM for sequential patterns, ensemble for final prediction.

**Why not just XGBoost?** Stock prices have temporal dependencies (trend, momentum) that tree-based models don't capture naturally. LSTM adds sequential awareness.

**Why not a Transformer?** For the amount of training data available to a personal tool (a few years of daily data for ~500 stocks), Transformers are overkill and prone to overfitting. LSTM is sufficient and trains faster.

**Why ensemble?** Each model captures different patterns. The ensemble averages their predictions weighted by recent accuracy, giving more robust confidence estimates.

## ML Safeguards

**Decision:** Aggressive anti-overfitting measures built into the architecture, not bolted on.

**Why this matters in finance:** In most ML applications, overfitting means slightly worse accuracy. In finance, overfitting means the model confidently predicts returns that don't exist, leading to real monetary losses.

Three safeguards:

1. **Point-in-time enforcement** — Every feature carries an `available_at` timestamp. The system mathematically cannot use future data for training. This prevents lookahead bias, the most common and devastating mistake in financial ML.

2. **Survivorship bias prevention** — The `UniverseManager` tracks which stocks existed at each historical point, including those later delisted. Training only on survivors (stocks that are still listed today) creates false optimism.

3. **Overfitting detector** — Uses the Deflated Sharpe Ratio (Bailey & López de Prado, 2014) which adjusts for multiple testing. If you test 100 strategies, the best one looks good by luck alone. Deflated Sharpe quantifies this.

## Transaction Cost Modelling

**Decision:** Model every fee component separately rather than using a flat "0.5% round-trip" estimate.

**Why:** India's fee structure is complex (STT, stamp duty, GST on brokerage, SEBI fee, exchange transaction charge). A flat estimate hides the true cost and makes paper trading results unrealistically optimistic.

Each component is individually configurable via YAML, so switching to US markets just means loading different cost parameters.

## Circuit Breaker: Four States

**Decision:** GREEN → AMBER → RED → BLACK state machine with automatic actions.

**Why not just a simple stop-loss?** A stop-loss protects one position. The circuit breaker protects the entire system. If the model's accuracy drops below 35% over 10 days (RED), or portfolio drawdown exceeds 15% (BLACK), something systemic is wrong — not just one bad pick.

**State actions:**
| State | Trigger | Action |
|-------|---------|--------|
| AMBER | 5-day accuracy < 40% | Cut position sizes by 50% |
| RED | 10-day accuracy < 35% or drawdown > 8% | Pause new entries, exits only |
| BLACK | Drawdown > 15% | Full stop, require manual reset |

**Why require manual reset from BLACK?** Automated recovery from a severe drawdown is dangerous. A human needs to assess whether the cause is a model failure, a market regime change, or a data problem.

## LLM Usage: Cost-Gated with Local Fallback

**Decision:** Use cloud LLMs (Gemini) for high-value tasks, with daily budget caps and automatic fallback to local Ollama.

**Why not all-cloud?** Running Bull/Bear debates for 500 stocks daily would cost hundreds of dollars. By limiting debate to the top 15 picks and capping daily spend at ₹50 (configurable), costs stay predictable.

**Why not all-local?** Local models (Llama 3.2 via Ollama) produce decent but lower-quality thesis text. Cloud models give better reasoning for the highest-conviction picks where quality matters most.

## Self-Improvement: Conservative by Design

**Decision:** Bayesian shrinkage with minimum samples, max change caps, and shadow validation.

**Why not just use whichever weights performed best?** Small samples create illusions. If "sentiment" happened to be right 80% of the time over 20 trades, that's probably luck, not a stable signal. The minimum 100-sample requirement prevents premature optimization.

**Why max 5% change per adjustment?** Prevents the system from dramatically swinging weights based on one good/bad period. Combined with the 30% shrinkage factor (blend 30% toward evidence, 70% toward current weights), this ensures gradual, stable adaptation.

**Why shadow A/B testing?** Even with Bayesian shrinkage, new weights might underperform in practice. Running them as a shadow portfolio for 2 weeks, with a statistical significance gate (p < 0.10), means we only adopt changes that demonstrably improve performance.

## Frontend: React + Vite + Tailwind

**Decision:** React 18 with TypeScript, Vite for builds, Tailwind CSS for styling.

**Why not Next.js?** This is a single-page dashboard application, not a content site. We don't need SSR, ISR, or file-based routing. Vite gives us faster builds and simpler configuration.

**Why Zustand over Redux?** The client state is simple — portfolio selection, settings preferences. Zustand's minimal API (no action creators, reducers, or middleware boilerplate) is proportional to the actual complexity.

**Why TradingView Lightweight Charts?** Purpose-built for financial charting with excellent performance. Alternatives like Chart.js or Recharts lack candlestick support and financial-specific features (crosshair, price scales, volume histograms).
