# Recommendation Engine

> **Location:** `backend/app/domain/recommendation/`
>
> **Purpose:** Convert composite scores into actionable trading signals with exit rules, thesis, and full audit trail.

## Signal Generation (`scoring.py`)

Each stock gets a signal for every time horizon:

| Horizon | Code | Typical Use |
|---------|------|-------------|
| 1 day | `1d` | Very short-term momentum |
| 3 days | `3d` | Short swing trades |
| 1 week | `1w` | Swing trading |
| 1 month | `1m` | Position trading |
| 3 months | `3m` | Conviction holds |

**Direction logic:**
- **BUY**: composite ≥ 65 AND expected return > 0
- **SELL**: composite ≤ 35 OR expected return < -3%
- **HOLD**: everything in between

Each signal carries:
- `strength` (0–100) — the composite score
- `expected_return_pct` — ML-predicted return for this horizon
- `confidence` (0–1) — calibrated probability (when model says 70%, it should be right 70% of the time)
- `independent_signal_count` — effective signals after decorrelation (higher = more trustworthy)

## Exit Rules (`exit_signals.py`)

Every BUY signal comes with predefined exit conditions. You don't just know _when to buy_ — you know _when to get out_.

### Trailing Stop-Loss
Default 7% below entry. If you buy at ₹100, the initial stop is at ₹93. As price rises to ₹120, the stop rises to ₹111.60. It never moves down — only up.

### ATR-Based Exit
ATR (Average True Range) measures how much a stock typically moves in a day. The stop is set at `entry_price - 2.5 × ATR`. A volatile stock (high ATR) gets a wider stop; a stable stock gets a tighter one. This adapts to each stock's personality.

### Technical Reversal Detection
The system watches for signs that a trend is exhausted:
- RSI > 75 (overbought) AND
- MACD histogram turns negative (momentum fading) AND/OR
- Volume ratio < 0.8 (buyers drying up)

When 2 of 3 conditions are met, a reversal warning fires.

### Time-Based Expiry
If no other trigger fires by the end of the signal's horizon, the position is reviewed. This prevents "zombie positions" that drift without conviction.

## LLM Debate (`application/recommender/debate.py`)

For the top 15 picks (gated by LLM budget), the system runs a structured debate:

```
┌──────────────┐         ┌──────────────┐
│  Bull Case   │         │  Bear Case   │
│              │         │              │
│ "This stock  │         │ "Risks here  │
│  should rise │         │  include...  │
│  because..." │         │  because..." │
└──────┬───────┘         └──────┬───────┘
       │                        │
       └────────┬───────────────┘
                │
       ┌────────▼────────┐
       │   Synthesis     │
       │                 │
       │ Weighs both     │
       │ sides, assigns  │
       │ scenario probs  │
       └─────────────────┘
```

The debate is streamed to the frontend via **Server-Sent Events** (SSE), so you see the bull/bear arguments appear in real-time.

**Cost management:** The `LLMCostTracker` monitors daily spend against a configurable budget (default ₹50/day). When budget is low, it automatically switches to Ollama (free, local). The tracker records every call with input/output tokens and cost.

## Thesis Generation (`application/recommender/service.py`)

Each recommendation can have a thesis — a structured investment narrative:
- **Entry triggers** — what specifically caused the BUY signal
- **Monitoring conditions** — what to watch while holding
- **Invalidation triggers** — what would make the thesis wrong

Theses are cached (TTL-based) so requesting the same stock twice doesn't re-invoke the LLM.

## Decision Audit (`models.py` → `DecisionAudit`)

Every recommendation is paired with a complete audit record:

```
DecisionAudit
├── correlation_id          ← trace the full request
├── ticker, horizon
├── decision (BUY/SELL/HOLD)
├── technical_score         ← raw input from each pillar
├── factor_score
├── sentiment_score
├── ml_prediction
├── weights_used            ← which weights were active
├── pillar_correlations     ← decorrelation results
├── effective_signal_count
├── composite_score         ← final combined score
├── confidence
├── risk_check_passed       ← did risk manager approve?
├── risk_check_reasons      ← if rejected, why?
├── data_quality_flags      ← any quality issues with input data
└── extra                   ← additional context
```

This is immutable — once written, it's never modified. This lets you debug any recommendation months later: "Why did the system recommend buying RELIANCE on March 15? What were the exact inputs?"

## Accuracy Tracking

After a signal's horizon expires, the system checks what actually happened:
- Did the stock move in the predicted direction?
- Was the actual return close to the predicted return?

This feeds back into:
1. **Calibration evaluation** — are confidence estimates accurate?
2. **Self-improvement** — which pillars are contributing to correct predictions?
3. **Circuit breaker** — rolling accuracy drives state transitions

## Key Files

| File | Purpose |
|------|---------|
| `models.py` | Signal, ExitRule, Thesis, DebateResult, DecisionAudit, Recommendation |
| `scoring.py` | `score_for_horizon()`, `generate_multi_horizon_signals()` |
| `exit_signals.py` | `generate_exit_rules()`, `check_technical_reversal()` |
| `application/recommender/debate.py` | LLM-powered Bull/Bear debate |
| `application/recommender/audit.py` | Decision audit recording |
