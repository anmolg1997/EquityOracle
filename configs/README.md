# Configs

YAML configuration files loaded at startup. All behavioral parameters are externalized here — changing strategy requires editing YAML, not Python.

## Files

```
configs/
├── markets/
│   ├── india.yaml               India market: NSE/BSE tickers, indices, timezone, currency
│   ├── us.yaml                  US market: NYSE/NASDAQ configuration
│   └── global.yaml              Global screener configuration
├── scanners/
│   ├── minervini.yaml           Mark Minervini's trend template filter
│   ├── canslim.yaml             CANSLIM growth criteria
│   ├── momentum_breakout.yaml   High RS + volume breakout filter
│   └── value_deep.yaml          Deep value (low P/E, high dividend yield)
├── composite_weights.yaml       Pillar weights: technical (0.25), fundamental (0.25), sentiment (0.20), ML (0.30)
├── risk.yaml                    Max positions (25), max position size (10%), drawdown thresholds
├── circuit_breaker.yaml         State transition thresholds and cooldown periods
└── autonomy.yaml                Per-engine autonomy levels (manual/semi_auto/full_auto)
```

## Adding a New Scanner Preset

Create a YAML file in `configs/scanners/`:

```yaml
name: "My Custom Screen"
description: "Stocks with strong momentum and reasonable valuation"
criteria:
  - field: rs_rating
    operator: gte
    value: 70
  - field: pe_ratio
    operator: lt
    value: 25
  - field: volume_ratio
    operator: gt
    value: 1.5
```

The scanner service auto-discovers YAML files in this directory. No code changes needed.
