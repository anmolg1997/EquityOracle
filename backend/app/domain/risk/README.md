# Risk Domain

Three layers of portfolio protection: pre-trade validation, market regime awareness, and automatic circuit breakers.

## Files

| File | Purpose |
|------|---------|
| `models.py` | `RiskCheckResult`, `DrawdownState`, `CircuitBreakerLog`, `PositionRiskMetrics` |
| `manager.py` | `RiskManager` — validates orders against position count, size limits, duplicates, and cash sufficiency |
| `regime.py` | `detect_regime()` — classifies market as bull/bear/sideways/uncertain using index MA alignment + breadth |
| `circuit_breaker.py` | `CircuitBreakerService` — four-state machine (GREEN→AMBER→RED→BLACK) with automatic transitions and audit trail |

## Key Concepts

- **Pre-trade validation** runs on every order. Multiple violations are collected and reported together, not short-circuited.
- **Regime detection** uses the Nifty 50 (or configured index) moving average alignment plus market breadth (% of stocks above 200-day MA).
- **Circuit breaker** monitors rolling accuracy and portfolio drawdown. AMBER cuts position sizes by 50%. RED pauses new entries. BLACK requires manual reset — this is intentional for severe failures.
- **DrawdownState** continuously tracks peak portfolio value and computes percentage decline. Resets when new highs are made.
