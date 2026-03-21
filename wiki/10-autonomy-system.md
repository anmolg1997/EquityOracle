# Autonomy System

> **Location:** `backend/app/application/autonomy/`
>
> **Purpose:** Allow the system to operate with configurable levels of independence — from fully manual to fully autonomous — while ensuring it can't harm itself through misguided self-improvement.

## Autonomy Levels

Each engine (scanner, recommender, paper trader, self-improvement) has an independent autonomy level:

| Level | Behavior | Example |
|-------|----------|---------|
| **Manual** | Does nothing without user action | Paper trading: user manually confirms each trade |
| **Semi-Auto** | Generates results, waits for approval | Recommender: generates signals, user approves execution |
| **Full-Auto** | Operates independently within safety bounds | Scanner: runs daily without any user input |

Default configuration:
```
scanner:          full_auto    (scanning is always automated)
recommender:      semi_auto    (generates recs, human approves trades)
paper_trader:     manual       (explicit user action needed)
self_improvement: semi_auto    (proposes changes, human confirms)
```

## Circuit Breaker Integration

The autonomy controller checks the circuit breaker before allowing any action:

| Circuit Breaker | Scanner | Recommender | Paper Trader | Self-Improvement |
|----------------|---------|-------------|--------------|-----------------|
| GREEN | Runs | Runs | Runs | Runs |
| AMBER | Runs | Runs | Runs (50% size) | Runs |
| RED | Runs | **Blocked** | **Blocked** | Runs |
| BLACK | **Blocked** | **Blocked** | **Blocked** | **Blocked** |

Even if an engine is set to `full_auto`, the circuit breaker can override it. This is the safety net that prevents autonomous operation from continuing during a system failure.

## Self-Improvement (`self_improve.py`)

### The Problem
The composite scoring weights (25% technical, 25% fundamental, 20% sentiment, 30% ML) are initial estimates. Over time, we learn which pillars actually contribute to accurate predictions. Shouldn't the system adjust?

### The Solution (Carefully)
Yes, but with heavy guardrails. Naive self-improvement is dangerous — a few lucky trades could convince the system that "sentiment is 90% of the signal," leading to disaster when sentiment noise dominates.

### Safeguard 1: Minimum Sample Size
No weight adjustment until each pillar has at least **100 evaluated predictions**. This prevents premature optimization from small samples.

```python
if min(sample_counts.values()) < 100:
    return ImprovementProposal(approved=False, reason="Insufficient samples")
```

### Safeguard 2: Maximum Change Cap
No single adjustment can change a pillar's weight by more than **5 percentage points**. Even if data strongly suggests sentiment should be 50% of the score, the maximum single-step change is `current_weight ± 0.05`.

### Safeguard 3: Bayesian Shrinkage
New weights are blended between evidence and current weights:
```
new_weight = 0.70 × current_weight + 0.30 × evidence_based_weight
```
This 70/30 blend means the system is conservative by default — it takes strong, persistent evidence to shift weights meaningfully.

### Safeguard 4: Normalization
After adjustment, weights are normalized to sum to 1.0. This prevents drift over multiple adjustment cycles.

### Immutable Change Log
Every proposal (approved or rejected) is logged with:
- Old weights and new weights
- Sample sizes used
- Evidence (per-pillar accuracy)
- Whether it was approved and why/why not

## A/B Testing (`ab_testing.py`)

### The Problem
Even with Bayesian shrinkage and max change caps, new weights might underperform in practice. How do you test without risking the live portfolio?

### The Solution: Shadow Portfolios
When new weights are proposed:
1. Create a **shadow portfolio** that uses the new weights
2. Run both live and shadow portfolios in parallel for **at least 14 days**
3. Record daily returns for both
4. After the test period, run a two-sample t-test
5. Only adopt new weights if shadow outperforms with **p < 0.10**

```python
svc = ABTestingService()
svc.start_test(proposed_weights={"technical": 0.30, "fundamental": 0.20, ...})

# Daily recording (automated)
for day in range(14):
    svc.record_daily(live_return=0.001, shadow_return=0.003)

# Evaluation
result = svc.evaluate()
# → ShadowPortfolioResult(
#     is_significant=True,
#     p_value=0.05,
#     recommendation="adopt"
# )
```

### Why p < 0.10 (not 0.05)?
Financial data is noisy. With only 14 days of data, even genuinely better weights might not reach p < 0.05. The 0.10 threshold balances between false positives and missing real improvements. Combined with the other safeguards (small max changes, shrinkage), the risk of adopting a bad change is low.

## Daily Pipeline (`pipeline.py`)

The autonomous daily pipeline orchestrates the full workflow:

```
6:30 PM IST
    │
    ├── Check circuit breaker → if BLACK, abort everything
    │
    ├── Run data ingestion (if scanner autonomy allows)
    │
    ├── Run quality gates
    │
    ├── Compute scores + ML predictions
    │
    ├── Generate recommendations
    │
    ├── Risk-check and execute approved trades (if autonomy allows)
    │
    ├── Update accuracy tracking
    │
    ├── Monthly: propose weight adjustments (if self-improvement allows)
    │
    └── Log pipeline run context with correlation ID
```

## Key Files

| File | Purpose |
|------|---------|
| `controller.py` | Per-engine autonomy levels + circuit breaker integration |
| `self_improve.py` | Bayesian weight adjustment with min samples + max change + shrinkage |
| `ab_testing.py` | Shadow portfolio A/B testing with statistical significance |
| `pipeline.py` | Full daily autonomous pipeline orchestration |
