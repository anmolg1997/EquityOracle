# Analysis Engine

> **Location:** `backend/app/domain/analysis/`
>
> **Purpose:** Score every stock across multiple independent dimensions, then combine them into a single composite score.

## The Scoring Model

Think of each stock getting graded on four subjects. Each subject has its own test, and the final grade is a weighted average:

```
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│  Technical │   │Fundamental │   │ Sentiment  │   │     ML     │
│  (25%)     │   │  (25%)     │   │  (20%)     │   │  (30%)     │
│            │   │            │   │            │   │            │
│ RSI, MACD  │   │ Momentum   │   │ FinBERT    │   │ XGBoost    │
│ ADX, BB    │   │ Quality    │   │ FII/DII    │   │ LSTM       │
│ SMA, EMA   │   │ Value      │   │ News       │   │ Ensemble   │
│ Volume, RS │   │            │   │            │   │            │
└─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
      │                │                │                │
      └────────────────┴────────────────┴────────────────┘
                              │
                    Decorrelation Check
                              │
                     Weighted Composite
                         (0 – 100)
```

## Technical Score (`technical.py`)

Uses `pandas-ta` to compute 50+ indicators from OHLCV data. The composite technical score (0–100) weights these signals:

| Indicator | What It Measures | Bullish Signal |
|-----------|-----------------|----------------|
| RSI (14) | Momentum speed | 30-40 (oversold bounce) |
| MACD histogram | Trend acceleration | Positive and rising |
| ADX (14) | Trend strength | > 25 (strong trend) |
| Bollinger position | Volatility positioning | Near lower band (0-0.3) |
| Volume ratio | Participation intensity | > 1.5x average |
| OBV trend | Volume-price agreement | Rising OBV confirms price |
| RS rating | Relative strength vs. universe | > 70 (top quartile) |

**RS Rating** is particularly important — it measures a stock's 6-month return relative to the entire universe. A stock with RS 90 has outperformed 90% of all stocks. This is the backbone of momentum investing.

## Factor Scores (`factors.py`)

Three independent factor scores, each 0-100:

### Momentum Factor
- **6-month return** (excluding the most recent month to avoid reversal effects)
- **12-month return** (same exclusion)
- Strong 6-month return (>30%) scores 75+; negative returns pull score below 50

### Quality Factor
- **3-year profit growth** — consistent growth > 20% scores high
- **Operating profit margin** — > 20% indicates pricing power
- **ROE** — > 20% means efficient use of shareholder capital

### Value Factor
- **P/E ratio** — < 12 is deep value (scores 70+), > 40 is expensive (scores 30-)
- **P/B ratio** — < 1.5 suggests undervaluation
- **EV/EBITDA** — < 8 is cheap relative to cash flows

The three factors combine equally: `composite = (momentum + quality + value) / 3`

## Decorrelation Check (`decorrelation.py`)

**The problem:** If Technical and Momentum scores both just measure "stock went up recently," they're counting the same signal twice. The composite score would be overconfident.

**The solution:** Before combining pillars, compute pairwise rank correlations. If two pillars correlate above 0.75, the redundant one gets its weight halved.

**Example:**
- Technical vs. Fundamental correlation: 0.15 → both keep full weight
- Technical vs. Momentum correlation: 0.82 → Momentum weight halved

The effective signal count tells you how many truly independent signals you have. 4 pillars with 2 highly correlated gives ~3.0 effective signals.

## Composite Scoring (`composite.py`)

```python
overall = tech_score × 0.25 + factor_score × 0.25 + sentiment × 0.20 + ml_prediction × 0.30
```

Weights are loaded from `configs/composite_weights.yaml` and tuned by the self-improvement system.

**Confidence levels** based on overall score:
- **High** (≥ 80): Strong conviction across multiple pillars
- **Medium** (60–80): Moderate agreement
- **Low** (< 60): Mixed or insufficient signals

## Scanner Presets (`application/scanner/`)

The scanner uses a declarative `FilterSpec` — a list of criteria that stocks must pass:

```yaml
# configs/scanners/minervini.yaml — Mark Minervini's trend template
criteria:
  - field: close
    operator: ">"
    reference: sma_150
  - field: close
    operator: ">"
    reference: sma_200
  - field: sma_50
    operator: ">"
    reference: sma_150
  - field: close
    operator: within_pct
    value: 25
    reference: high_52w
```

This reads as: "Stock must be above its 150-day and 200-day moving averages, 50-day MA must be above 150-day MA, and price must be within 25% of its 52-week high."

Available presets: Minervini, CANSLIM, Momentum Breakout, Deep Value.

## Key Files

| File | Purpose |
|------|---------|
| `models.py` | TechnicalScore, FactorScore, SentimentScore, CompositeScore, ScanResult |
| `technical.py` | 50+ indicator computation via pandas-ta |
| `factors.py` | Momentum, Quality, Value factor scoring |
| `composite.py` | Weighted pillar aggregation |
| `decorrelation.py` | Pairwise rank correlation and effective signal count |
| `application/scanner/filter_spec.py` | Declarative filter builder with 8 operators |
| `application/scanner/presets.py` | YAML preset loader |
