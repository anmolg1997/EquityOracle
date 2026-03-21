# Portfolio Domain

Paper trading engine with realistic transaction costs, slippage, and tax modelling.

## Files

| File | Purpose |
|------|---------|
| `models.py` | `Order`, `Fill`, `Position` (with PnL tracking), `Portfolio` (cash + positions + aggregates), `PerformanceMetrics` |
| `engine.py` | `PortfolioEngine` — processes buys and sells with slippage + costs. Tracks gross vs. net P&L |
| `costs.py` | `TransactionCostModel` (STT, stamp duty, GST, SEBI fee, exchange charge), `SlippageModel` (market-cap-aware, quadratic with participation rate), `TaxModel` (STCG 20%, LTCG 12.5%) |
| `sizing.py` | Four strategies: `EqualWeight`, `ConvictionWeighted`, `RiskParity`, `Kelly`. All respect max-position-pct and liquidity caps |
| `ports.py` | `PortfolioRepository` abstract interface |

## Key Concepts

- **Gross vs. net P&L** — gross is the strategy's theoretical return; net is what you'd actually take home after all costs. The gap is often 1–3% annually.
- **Slippage scales quadratically** with order size relative to daily volume. A 1% participation rate is negligible; 10% is significant.
- **Tax is estimated per position** based on holding period. Carry-forward of losses is simplified.
- All cost components are individually configurable via YAML for multi-market support.
