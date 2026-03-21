# Market Data Domain

Ingests, validates, and serves stock price and fundamental data. This is the first bounded context in the pipeline — all downstream analysis depends on clean data from here.

## Files

| File | Purpose |
|------|---------|
| `models.py` | `OHLCV`, `FundamentalData`, `InsiderDeal`, `InstitutionalFlow`, `MarketBreadth`, `LiquidityProfile` — all with `available_at` for point-in-time |
| `quality.py` | Five quality checks: freshness, split detection, outlier, cross-source divergence, delisting detection. Batch `run_quality_gate()` runs all checks |
| `liquidity.py` | Computes `LiquidityProfile`, classifies market cap, estimates market impact, gates entry via `passes_liquidity_filter()` |
| `ports.py` | `MarketDataProvider` (abstract: fetch OHLCV, fundamentals) and `MarketDataRepository` (abstract: persist/query) |
| `services.py` | Data validation service, split adjustment logic |

## Key Concepts

- **Quality gate** prevents bad data from reaching analysis. Each check returns a `QualityCheckResult` with a flag and explanation; `None` means the data passed.
- **Liquidity scoring** uses 20-day average daily value. Market cap classification: large (≥₹50Cr daily), mid (≥₹5Cr), small (≥₹50L), micro (<₹50L).
- **Market impact** is modelled quadratically with participation rate — order sizes above 10% of daily volume are marked infeasible.
- Every model carries `available_at` to support point-in-time queries (see [ML Pipeline](../../../wiki/09-ml-pipeline.md)).
