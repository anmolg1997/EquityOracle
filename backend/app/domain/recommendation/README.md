# Recommendation Domain

Converts composite scores into actionable trading signals with exit rules and full audit trails.

## Files

| File | Purpose |
|------|---------|
| `models.py` | `Signal`, `ExitRule`, `Thesis`, `DebateResult`, `DecisionAudit`, `Recommendation` |
| `scoring.py` | `score_for_horizon()` — maps composite score to BUY/SELL/HOLD per time horizon. `generate_multi_horizon_signals()` — produces signals for all 5 horizons |
| `exit_signals.py` | `generate_exit_rules()` — creates trailing stop, ATR-based, and time-based exits. `check_technical_reversal()` — detects overbought + fading momentum |
| `ports.py` | `RecommendationRepository` abstract interface |

## Key Concepts

- **Every BUY signal comes with exit rules.** You always know when to get out before you get in.
- **Multi-horizon signals** cover 1d, 3d, 1w, 1m, 3m — the same stock can be a BUY on the monthly horizon but HOLD on the daily.
- **DecisionAudit** is immutable — full context of every recommendation for debugging and accountability.
- **ExitRule.is_triggered(current_price)** returns True when the exit condition is met.
