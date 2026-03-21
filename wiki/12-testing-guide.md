# Testing Guide

> **Location:** `backend/tests/`
>
> **Framework:** pytest + pytest-asyncio

## Test Philosophy

Every piece of domain logic is tested without external infrastructure (no database, no Redis, no API calls). Tests run in under 1 second because the architecture keeps domain pure.

Integration tests verify that domains work correctly when wired together — still without external services, just verifying the function call chains produce correct results.

## Running Tests

```bash
cd backend
source .venv/bin/activate

# All tests
pytest tests/ -v

# Just domain unit tests (fastest feedback)
pytest tests/unit/domain/ -v

# Just integration tests
pytest tests/integration/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Specific module
pytest tests/unit/portfolio/ -v

# Single test
pytest tests/unit/domain/test_circuit_breaker.py::TestCircuitBreaker::test_starts_green -v
```

## Test Structure

```
tests/
├── conftest.py                              # Shared fixtures (sample tickers, OHLCV data)
├── unit/
│   ├── domain/                              # Core domain models and logic
│   │   ├── test_types.py                    # Ticker, DateRange, enums
│   │   ├── test_events.py                   # EventBus pub/sub
│   │   ├── test_exceptions.py               # Exception hierarchy
│   │   ├── test_market_data_models.py       # OHLCV, InstitutionalFlow, MarketBreadth
│   │   ├── test_quality.py                  # Data quality gate (5 checks)
│   │   ├── test_quality_edge_cases.py       # Edge cases: zero open, split boundary
│   │   ├── test_liquidity.py                # Liquidity scoring, market impact
│   │   ├── test_costs.py                    # Transaction costs, slippage, tax
│   │   ├── test_circuit_breaker.py          # State machine transitions
│   │   ├── test_decorrelation.py            # Pillar independence checks
│   │   └── test_recommendation_models.py    # ExitRule triggering, DecisionAudit
│   ├── analysis/
│   │   ├── test_factors.py                  # Momentum, Quality, Value scoring
│   │   ├── test_composite.py                # Weighted composite aggregation
│   │   └── test_filter_spec.py              # FilterSpec builder (all operators)
│   ├── recommendation/
│   │   ├── test_scoring.py                  # Signal generation, multi-horizon
│   │   └── test_exit_signals.py             # Exit rules, technical reversal
│   ├── portfolio/
│   │   ├── test_engine.py                   # Buy/sell lifecycle with costs
│   │   ├── test_models.py                   # Position PnL, Portfolio aggregates
│   │   └── test_sizing.py                   # 4 sizing strategies + liquidity cap
│   ├── risk/
│   │   ├── test_risk_manager.py             # Pre-trade validation
│   │   ├── test_regime.py                   # Bull/bear/sideways detection
│   │   └── test_drawdown.py                 # Peak tracking, recovery
│   ├── autonomy/
│   │   ├── test_controller.py               # Engine configs + CB integration
│   │   ├── test_self_improve.py             # Bayesian adjustment with safeguards
│   │   └── test_ab_testing.py               # Shadow portfolio testing
│   ├── ml/
│   │   ├── test_point_in_time.py            # Lookahead bias detection
│   │   ├── test_point_in_time_extended.py   # Training labels, edge cases
│   │   ├── test_calibration.py              # ECE evaluation
│   │   ├── test_overfitting.py              # Deflated Sharpe, IS/OOS, stability
│   │   ├── test_universe_manager.py         # Survivorship bias checks
│   │   └── test_attribution.py              # Feature importance categorization
│   ├── infra/
│   │   └── test_cost_tracker.py             # LLM budget, usage recording
│   └── api/
│       ├── test_health_endpoints.py         # Health, portfolio, autonomy endpoints
│       └── test_middleware.py               # Correlation ID, timing headers
└── integration/
    ├── test_recommendation_pipeline.py      # Data → score → signal → exit rules
    ├── test_portfolio_flow.py               # Risk check → buy → sell → PnL
    ├── test_autonomy_flow.py                # CB + autonomy + self-improvement
    └── test_data_quality_pipeline.py        # Quality → liquidity → decorrelation
```

## Test Count by Module

| Module | Tests | What's Verified |
|--------|-------|----------------|
| Domain / Core | 103 | Value objects, events, exceptions, models, quality, liquidity, costs, circuit breaker |
| ML Safeguards | 37 | Point-in-time, calibration, overfitting, universe, attribution |
| Analysis | 28 | Factors, composite, filter spec |
| Recommendation | 22 | Scoring, exit signals, model properties |
| Portfolio | 30 | Engine lifecycle, sizing, model properties |
| Risk | 17 | Risk manager, regime, drawdown |
| Autonomy | 24 | Controller, self-improvement, A/B testing |
| Infrastructure | 9 | LLM cost tracker |
| API | 10 | Endpoints, middleware |
| Integration | 20 | Cross-domain flows |
| **Total** | **300** | |

## What Makes a Good Test Here

### Tests verify business rules, not implementation
```python
# Good: tests the RULE that a 20% price drop with normal volume = suspected split
def test_split_detected(self, ticker):
    yesterday = _make_ohlcv(ticker, date(2024, 3, 14), Decimal("3500"), volume=1_000_000)
    today = _make_ohlcv(ticker, date(2024, 3, 15), Decimal("1750"), volume=1_500_000)
    result = check_split_or_corporate_action(today, yesterday)
    assert result.flag == DataQualityFlag.SPLIT_SUSPECTED
```

### Integration tests verify the chain, not individual components
```python
# Good: tests the full flow from risk check to buy to sell
def test_full_buy_sell_cycle(self, ticker, portfolio):
    engine = PortfolioEngine(portfolio)
    order = Order(ticker=ticker, side=OrderSide.BUY, quantity=100)
    engine.process_buy(order, fill_price=Decimal("3500"))
    assert len(portfolio.open_positions) == 1

    pos = portfolio.open_positions[0]
    engine.process_sell(pos, sell_price=Decimal("3800"))
    assert not pos.is_open
```

## Coverage

Domain and ML modules are at **84% coverage**. Infrastructure modules (database, Redis, external APIs) are at 0% — they require running services and are tested via integration tests when infrastructure is available.

To generate an HTML coverage report:
```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```
