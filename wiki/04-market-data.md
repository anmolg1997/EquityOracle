# Market Data Domain

> **Location:** `backend/app/domain/market_data/`
>
> **Purpose:** Fetch, validate, and serve stock price and fundamental data.

## Finance Concepts You Need

**OHLCV** — Open, High, Low, Close, Volume. Every trading day, a stock has these five numbers. Open is the first trade price, close is the last, high/low are the extremes, volume is how many shares traded.

**Fundamentals** — Financial metrics derived from a company's accounting statements: P/E ratio (price relative to earnings), ROE (how efficiently a company uses shareholder money), debt-to-equity, profit growth.

**Insider deals** — When company directors or large shareholders buy/sell shares. Bulk deals (large single trades) and promoter buying are often seen as bullish signals.

**Institutional flows** — FII (Foreign Institutional Investors) and DII (Domestic Institutional Investors) are large players whose buying/selling patterns can move markets. Net FII buying is generally bullish for Indian markets.

## Data Models

```
OHLCV
├── ticker: Ticker (symbol + exchange + market)
├── date: date
├── open, high, low, close: Decimal
├── volume: int
├── data_quality: DataQualityFlag (ok / stale / outlier / ...)
└── available_at: datetime  ← point-in-time: when this row became available

FundamentalData
├── pe_ratio, pb_ratio, ev_ebitda
├── roe, roce, debt_to_equity
├── revenue_growth_3yr, profit_growth_3yr
├── operating_profit_margin
├── promoter_holding_pct
└── sector, industry

LiquidityProfile
├── avg_daily_volume_20d
├── avg_daily_value_20d
├── market_cap_category: "large" / "mid" / "small" / "micro"
└── liquidity_score: 0-100
```

## Data Quality Gate (`quality.py`)

Every data point passes through 5 checks before entering the system:

### 1. Freshness Check
If the latest record is more than 3 business days old (accounting for weekends), it's flagged `STALE`. This prevents generating signals on prices that are a week old because a provider went down.

### 2. Split/Corporate Action Detection
A stock split makes the price drop by 50% overnight — but that's not a crash. The system detects this by looking for large price changes (>20%) that are NOT accompanied by extreme volume spikes. A real crash has both a price drop AND a 10x volume surge. A split has a price drop with normal volume.

### 3. Outlier Detection
If today's return is more than 4 standard deviations from the historical mean, it's flagged. This catches data entry errors (a decimal point in the wrong place) without filtering out legitimate extreme moves.

### 4. Cross-Source Divergence
When two data sources report the same stock's close price, they should agree within 0.5%. If yfinance says ₹3500 and Alpha Vantage says ₹3600, something is wrong with one of them.

### 5. Delisting Detection
If a stock has zero volume for 10+ consecutive days, it's likely delisted or suspended. These get flagged before they pollute the universe.

## Liquidity Scoring (`liquidity.py`)

**Why this matters:** If a stock trades ₹50,000 per day and you want to buy ₹5,00,000 worth, your order _is_ the entire market for 10 days. Your buying will push the price up (market impact), and when you sell, it'll push the price down. The slippage can eat your entire profit.

**How it works:**
1. Compute 20-day average daily traded value (price × volume)
2. Classify: large (≥₹50Cr), mid (≥₹5Cr), small (≥₹50L), micro (<₹50L)
3. Score 0–100 based on daily traded value thresholds
4. `passes_liquidity_filter()` gates entry — stocks below minimum liquidity are excluded from recommendations

**Market impact estimation:**
```
participation_rate = order_value / avg_daily_value
slippage = base_slippage × (1 + participation_rate²)
```
The quadratic scaling means a 1% participation rate adds minimal slippage, but a 10% rate adds substantial slippage. Orders above 10% of daily volume are marked infeasible.

## Data Provider Resilience (`infrastructure/data_providers/resilience.py`)

The `ResilientDataProvider` wraps multiple concrete providers:

```
Request → Provider 1 (yfinance)
              │
              ├── Success → return data, reset failure counter
              │
              └── Failure → log warning, try next
                    │
                    ▼
              Provider 2 (Alpha Vantage)
                    │
                    ├── Success → return data
                    │
                    └── Failure → log warning, try next
                          │
                          ▼
                    Provider 3 (TradingView)
                          │
                          └── Failure → raise ProviderUnavailableError
```

Each provider tracks its own health: consecutive failures, last success time, average latency. This information feeds the Provider Health panel in the UI.

## Key Files

| File | Purpose |
|------|---------|
| `models.py` | OHLCV, FundamentalData, InsiderDeal, InstitutionalFlow, MarketBreadth, LiquidityProfile |
| `quality.py` | All 5 quality checks + batch `run_quality_gate()` |
| `liquidity.py` | Liquidity scoring, filtering, market impact estimation |
| `ports.py` | `MarketDataProvider` and `MarketDataRepository` abstract interfaces |
| `services.py` | Data validation and split adjustment logic |
