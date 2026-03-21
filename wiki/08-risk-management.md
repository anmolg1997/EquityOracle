# Risk Management

> **Location:** `backend/app/domain/risk/`
>
> **Purpose:** Protect the portfolio from catastrophic losses through pre-trade validation, market regime awareness, and automatic circuit breakers.

## Philosophy

The best recommendation system in the world is useless if one bad week wipes out six months of gains. Risk management isn't about avoiding losses — it's about ensuring losses stay small enough that you can recover.

Three layers of protection:

```
Layer 1: Pre-Trade Risk Manager
         ↓ (validates every order)
Layer 2: Market Regime Detection
         ↓ (adjusts strategy for market conditions)
Layer 3: Circuit Breaker
         ↓ (emergency stop when system performance degrades)
```

## Layer 1: Risk Manager (`manager.py`)

Every order passes through pre-trade validation before execution:

### Position Count Limit
Default: max 25 open positions. Beyond this, the portfolio becomes too fragmented to manage and monitor effectively.

### Position Size Limit
No single position can exceed 10% of portfolio value. This prevents concentration risk — if one stock drops 50%, the portfolio loses at most 5%.

### Duplicate Check
Can't buy a stock you already hold. This prevents accidental doubling down.

### Cash Sufficiency
Order value (including estimated costs) must not exceed available cash.

All checks run together. If multiple fail, all reasons are reported:
```python
result = risk_mgr.validate_order(order, order_value, portfolio)
# result.approved = False
# result.reasons = ["Position size 15.0% exceeds max 10.0%",
#                    "Already holding RELIANCE:NSE"]
```

## Layer 2: Regime Detection (`regime.py`)

Markets have moods. A strategy that works in a bull market can be disastrous in a bear market.

**How it works:**
1. Look at the market index (e.g., NIFTY 50)
2. Compare current price to its 50-day and 200-day moving averages
3. Factor in market breadth (what percentage of stocks are above their 200-day MA)

| Condition | Regime |
|-----------|--------|
| Price > SMA50 > SMA200 | **Bull** — trend is up, proceed normally |
| Price < SMA50 < SMA200 | **Bear** — trend is down, reduce exposure |
| Mixed signals | **Sideways** — choppy, be selective |
| Less than 200 days of data | **Uncertain** — not enough history |

Breadth provides refinement:
- >60% of stocks above 200-day MA → leans bullish
- <30% of stocks above 200-day MA → leans bearish

## Layer 3: Circuit Breaker (`circuit_breaker.py`)

The circuit breaker is a state machine that monitors system performance and automatically takes defensive action when things go wrong.

### State Machine

```
                ┌───────┐
                │ GREEN │  Normal operations
                └───┬───┘
                    │ 5-day accuracy < 40%
                    ▼
                ┌───────┐
                │ AMBER │  Position sizes cut by 50%
                └───┬───┘
                    │ 10-day accuracy < 35%  OR  drawdown > 8%
                    ▼
                ┌───────┐
                │  RED  │  No new entries, exits only
                └───┬───┘
                    │ Drawdown > 15%
                    ▼
                ┌───────┐
                │ BLACK │  Full stop, manual reset required
                └───────┘
```

### What Each State Does

| State | New Entries? | Position Size | Autonomy |
|-------|-------------|---------------|----------|
| GREEN | Yes | 100% | Full |
| AMBER | Yes | 50% of normal | Reduced |
| RED | No | 0% (exits only) | Minimal |
| BLACK | No | 0% (flatten to cash) | None |

### Recovery

From GREEN, AMBER, or RED: the system can auto-recover when metrics return to normal. For example, if AMBER was triggered by low accuracy and accuracy recovers above 40%, the system returns to GREEN.

From BLACK: **manual reset only.** This is intentional — a 15% drawdown indicates something fundamentally wrong (model failure, market regime change, data problem). A human needs to investigate before restarting.

### Audit Trail

Every state transition is logged immutably:
```
CircuitBreakerLog
├── previous_state: AMBER
├── new_state: RED
├── trigger_reason: "10d accuracy 0.30 < 0.35"
├── timestamp: 2024-03-15T10:30:00
└── metrics: {...}
```

## Drawdown Tracking (`models.py` → `DrawdownState`)

Drawdown measures the decline from a portfolio's peak value:

```
Peak value:    ₹12,00,000
Current value: ₹10,20,000
Drawdown:      15% [(12L - 10.2L) / 12L × 100]
```

The drawdown tracker:
1. Continuously tracks the highest portfolio value seen (peak)
2. Computes current drawdown as percentage decline from peak
3. Peak updates automatically when portfolio hits new highs
4. After a drawdown and recovery, drawdown resets to 0%

## How the Layers Work Together

```
New recommendation arrives: BUY RELIANCE at ₹2500, quantity 100
    │
    ▼
Circuit Breaker check:
    State = GREEN? → proceed
    State = AMBER? → proceed but size × 0.5
    State = RED/BLACK? → reject
    │
    ▼
Risk Manager validation:
    Position count OK? ✓
    Position size ≤ 10%? ✓
    No duplicate? ✓
    Cash sufficient? ✓
    │
    ▼
Portfolio Engine executes with realistic costs
    │
    ▼
After fill: update drawdown tracker, check circuit breaker
```

## Key Files

| File | Purpose |
|------|---------|
| `manager.py` | Pre-trade risk validation |
| `regime.py` | Bull/bear/sideways market classification |
| `circuit_breaker.py` | Four-state circuit breaker with audit |
| `models.py` | RiskCheckResult, DrawdownState, CircuitBreakerLog |
