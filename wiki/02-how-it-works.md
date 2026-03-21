# How It Works

This page walks through the complete pipeline: from raw market data entering the system to a ranked recommendation appearing in the UI. Read this to understand the end-to-end flow.

## The Daily Pipeline

Every trading day, EquityOracle runs this sequence:

```
 6:30 PM IST (after market close)
          │
          ▼
┌──────────────────┐
│  1. INGEST DATA  │  Fetch OHLCV, fundamentals, insider deals, FII/DII flows
└────────┬─────────┘
         ▼
┌──────────────────┐
│  2. QUALITY GATE │  Check freshness, detect splits, flag outliers
└────────┬─────────┘
         ▼
┌──────────────────┐
│  3. ANALYZE      │  Compute technical indicators, factor scores, sentiment
└────────┬─────────┘
         ▼
┌──────────────────┐
│  4. PREDICT      │  ML ensemble generates return predictions per horizon
└────────┬─────────┘
         ▼
┌──────────────────┐
│  5. SCORE        │  Weighted composite of 4 pillars → overall score
└────────┬─────────┘
         ▼
┌──────────────────┐
│  6. RECOMMEND    │  Generate signals, exit rules, thesis, debate (top picks)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  7. RISK CHECK   │  Position limits, drawdown, circuit breaker gate
└────────┬─────────┘
         ▼
┌──────────────────┐
│  8. EXECUTE      │  Paper portfolio: fill at next-day open with costs
└────────┬─────────┘
         ▼
┌──────────────────┐
│  9. LEARN        │  Track outcomes, adjust weights if evidence is strong
└──────────────────┘
```

## Step by Step

### Step 1 — Data Ingestion

**What happens:** The ingestion service pulls data for every stock in the configured universe (e.g., NSE 500).

**Data sources:**
- **OHLCV prices** — yfinance (primary), with Alpha Vantage as fallback
- **Fundamentals** — P/E, ROE, debt ratios, profit growth from screener/nselib
- **Insider deals** — Bulk/block deals, promoter buying/selling via nselib
- **Institutional flows** — FII (Foreign) and DII (Domestic) daily net buy/sell
- **News** — NewsAPI headlines for sentiment scoring

**Resilience:** Each data source is wrapped in a `ResilientDataProvider` that tries providers in sequence. If yfinance is down, it automatically falls back to the next source. Health status is tracked and shown in the UI.

### Step 2 — Quality Gate

**Why it matters:** Bad data produces bad recommendations. A stock split can look like a 50% crash. Stale data can generate signals on prices that are days old.

**What's checked:**
| Check | What It Catches |
|-------|----------------|
| Freshness | Data older than 3 business days |
| Split detection | Price drops >20% without proportional volume spike |
| Outlier detection | Daily returns beyond 4 standard deviations |
| Cross-source divergence | Two sources disagree on price by >0.5% |
| Delisting detection | 10+ consecutive zero-volume days |

Records that fail are flagged but not silently dropped — they're quarantined so you can investigate.

### Step 3 — Analysis

Three independent scoring pillars run on clean data:

**Technical Analysis** (via pandas-ta):
- RSI, MACD, ADX, Bollinger Bands, ATR, OBV
- SMA/EMA (20, 50, 150, 200 day)
- Volume ratio (current vs. 20-day average)
- Relative Strength (RS) rating — 6-month return percentile

**Factor Scoring:**
- **Momentum** — 6-month and 12-month returns, excluding the most recent month (avoids short-term reversal noise)
- **Quality** — 3-year profit growth + operating margin + ROE
- **Value** — P/E, P/B, EV/EBITDA

**Sentiment:**
- FinBERT (local transformer model) scores recent news headlines
- Institutional flow direction (are FIIs buying or selling?)

### Step 4 — ML Prediction

The ML pipeline generates expected returns and direction probabilities for each time horizon.

**Models:**
- XGBoost gradient boosted classifier
- PyTorch LSTM for sequential patterns
- Ensemble combines both with learned weights

**Safeguards (critical):**
- **Point-in-time enforcement** — Every feature carries an `available_at` timestamp. Features from the future are automatically rejected.
- **Walk-forward validation** — Train on Jan–Jun, validate on Jul–Sep, test on Oct–Dec. Slides forward over time.
- **Overfitting detector** — Checks Deflated Sharpe ratio (adjusts for multiple testing), in-sample/out-of-sample ratio, and feature importance stability across folds.

### Step 5 — Composite Scoring

The four pillars combine into a single 0–100 score:

```
Overall = 0.25 × Technical + 0.25 × Fundamental + 0.20 × Sentiment + 0.30 × ML
```

Before combining, a **decorrelation check** ensures pillars are actually measuring different things. If two pillars are >75% rank-correlated, the redundant one gets down-weighted by 50%.

Weights are configurable in `configs/composite_weights.yaml` and get tuned by the self-improvement system.

### Step 6 — Recommendation

**Signal generation:** For each stock above a threshold score, generate a signal per horizon:
- Score ≥ 65 and positive expected return → **BUY**
- Score ≤ 35 or expected return < -3% → **SELL**
- Otherwise → **HOLD**

**Exit rules** are attached to every BUY signal:
- Trailing stop-loss (default 7% below entry)
- ATR-based stop (2.5× ATR below entry)
- Time-based expiry (exit at horizon end if no trigger fires)

**For top 15 picks**, an LLM debate runs:
- Bull case and bear case are generated independently
- A synthesis weighs the arguments
- Cost-gated: debate only runs if LLM daily budget permits; otherwise falls back to Ollama (free)

### Step 7 — Risk Check

Before any paper trade executes, the risk manager validates:
- Position count within limit (default 25)
- Position size within 10% of portfolio value
- No duplicate holdings
- Sufficient cash
- Circuit breaker in GREEN or AMBER

### Step 8 — Portfolio Execution

Paper trades fill at the **next day's opening price** (no same-day fills — realistic for non-intraday).

**Cost modelling (India):**
| Fee | Rate |
|-----|------|
| Brokerage | 0.03% |
| STT | 0.1% (buy + sell) |
| Exchange transaction | 0.00345% |
| GST on brokerage | 18% |
| Stamp duty (buy only) | 0.015% |
| SEBI fee | 0.0001% |

Slippage scales quadratically with participation rate (order size relative to daily volume).

### Step 9 — Self-Improvement

Monthly, the system evaluates which pillars contributed most to accurate predictions:
1. Computes per-pillar accuracy over the last period
2. Proposes new weights via Bayesian shrinkage (max 5% change per pillar)
3. Runs the new weights as a shadow portfolio for 2 weeks
4. Only adopts if shadow outperforms with p < 0.10 (statistical significance)

This is gated by a minimum of 100 samples per bucket to prevent premature adjustment.
