# Portfolio Simulator

> **Location:** `backend/app/domain/portfolio/`
>
> **Purpose:** Simulate real trading with realistic costs, slippage, and tax — so paper results closely match what you'd get with real money.

## Why Realistic Simulation Matters

Most stock screeners say "this stock returned 40% in 3 months." But they ignore:
- **Transaction costs** — buying and selling a stock in India costs ~0.3% round-trip in fees alone
- **Slippage** — your order moves the price, especially for small/mid-cap stocks
- **Tax** — short-term gains are taxed at 20%, eating into profits
- **Cash constraints** — you can't buy every recommendation; capital is limited

EquityOracle models all of these. The "gross P&L" shows how the strategy performed before costs. The "net P&L" shows what you'd actually take home. The gap between them is often sobering.

## The Portfolio Engine (`engine.py`)

The engine processes orders through a realistic lifecycle:

```
Order submitted
      │
      ▼
  Risk Manager validates
      │
      ├── Rejected → log reason, skip
      │
      ▼
  Calculate slippage (volume-aware)
      │
      ▼
  Calculate transaction costs (per component)
      │
      ▼
  Execute fill at effective price
      │
      ▼
  Update portfolio cash and positions
```

### Buy Processing
1. Compute gross value: `fill_price × quantity`
2. Estimate slippage based on order size vs. daily volume
3. Compute each transaction cost component
4. Effective price = `fill_price + slippage_per_share`
5. Deduct `gross_value + slippage + transaction_cost` from cash
6. Create position with entry price = effective price

### Sell Processing
1. Compute gross proceeds: `sell_price × quantity`
2. Estimate slippage (reduces effective price)
3. Compute transaction costs
4. Estimate capital gains tax based on holding period
5. Add `gross_proceeds - slippage - costs` to cash
6. Close position, record exit details

## Transaction Cost Model (`costs.py`)

India-specific, each component modelled separately:

| Fee | Rate | Applied To |
|-----|------|------------|
| Brokerage | 0.03% | All trades |
| STT (Securities Transaction Tax) | 0.1% | Buy and sell |
| Exchange transaction charge | 0.00345% | All trades |
| GST on brokerage | 18% of brokerage | All trades |
| Stamp duty | 0.015% | Buy only |
| SEBI fee | 0.0001% | All trades |

For a ₹10,00,000 buy order, total costs are approximately ₹1,450 (0.145%).

The breakdown is exposed via `model.breakdown()` so you can see exactly where every rupee goes.

## Slippage Model

Slippage represents the price impact of your order. In a liquid large-cap (e.g., Reliance), buying ₹5L moves the price negligibly. In a micro-cap trading ₹50K/day, buying ₹5L is catastrophic.

```
participation_rate = order_value / avg_daily_volume_value
impact_multiplier = 1 + participation_rate² × 100
slippage = base_slippage × impact_multiplier × order_value
```

Base slippage by market cap:
| Category | Base Slippage |
|----------|--------------|
| Large | 0.05% |
| Mid | 0.10% |
| Small | 0.20% |
| Micro | 0.50% |

## Tax Model

Indian capital gains tax rules:

| Type | Holding Period | Rate | Exemption |
|------|---------------|------|-----------|
| STCG | < 12 months | 20% | None |
| LTCG | ≥ 12 months | 12.5% | First ₹1,25,000 per year |

The system estimates tax on each closed position. Losses are tracked but carry-forward logic is simplified.

## Position Sizing (`sizing.py`)

Four strategies for deciding how much to invest in each recommendation:

### Equal Weight
Allocate the same percentage (e.g., 10%) to every position. Simple, diversified.

### Conviction Weighted
Scale position size with confidence: a 90% confidence pick gets a larger allocation than a 50% one. Maps confidence (0.5–1.0) to 50–100% of max position size.

### Risk Parity
Target equal risk contribution: low-volatility stocks get larger positions, high-volatility stocks get smaller ones. If target risk is 2% and a stock's daily vol is 1%, it gets a 2× larger position than a stock with 2% daily vol.

### Kelly Criterion
Mathematically optimal sizing based on win rate and average win/loss ratio. Uses half-Kelly for safety (full Kelly is aggressive). Only allocates when there's a positive expected edge.

All strategies are capped by:
1. **Max position percentage** (default 10% of portfolio)
2. **Liquidity cap** — position can't exceed 5% of the stock's daily traded value

## Portfolio Tracking

The `Portfolio` model provides:
- `open_positions` — currently held
- `closed_positions` — exited
- `invested_value` — sum of current_price × quantity for open positions
- `total_value` — cash + invested_value
- `gross_pnl` — P&L before costs
- `net_pnl` — P&L after costs, slippage, and tax
- `total_return_pct` — net return on initial capital

Each `Position` independently tracks:
- Entry/exit prices and dates
- Entry/exit costs
- Total slippage
- Estimated tax
- Hold days
- Gross and net return percentages

## Key Files

| File | Purpose |
|------|---------|
| `models.py` | Order, Fill, Position, Portfolio, PerformanceMetrics |
| `engine.py` | `process_buy()`, `process_sell()`, `update_prices()` |
| `costs.py` | TransactionCostModel, SlippageModel, TaxModel |
| `sizing.py` | 4 sizing strategies + liquidity cap |
