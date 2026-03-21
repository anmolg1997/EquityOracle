# ML Pipeline

> **Location:** `backend/app/ml/`
>
> **Purpose:** Predict stock returns and direction using machine learning, with aggressive safeguards against the unique pitfalls of financial ML.

## Why Financial ML Is Hard

In a typical ML application (image classification, recommendation systems), overfitting means slightly worse accuracy. In finance, overfitting means the model **confidently predicts returns that don't exist**, leading to systematic losses. Three problems make financial ML uniquely treacherous:

1. **Lookahead bias** — Accidentally using information that wasn't available at prediction time. Example: using a company's Q4 earnings to predict Q3 stock movement.

2. **Survivorship bias** — Training only on stocks that exist today ignores all the companies that went bankrupt, were delisted, or were acquired. This makes historical returns look better than they were.

3. **Overfitting to noise** — Stock returns are extremely noisy. A model can "learn" patterns that are just random coincidence, especially with many features and limited data.

EquityOracle has dedicated safeguards for each.

## Feature Engineering (`features/`)

### Point-in-Time Features
Every feature carries an `available_at` timestamp:

```python
OHLCV(
    ticker=..., date=date(2024, 3, 15),
    close=Decimal("2500"), ...,
    available_at=datetime(2024, 3, 15, 15, 30)  # when this data became available
)
```

The `FeatureEngineer` automatically filters: when building features for a prediction on March 15, any data with `available_at > March 15` is excluded. This is enforced at the infrastructure level, not left to individual feature authors.

### Feature Categories

**Technical features** (`technical_features.py`):
- Returns over multiple windows (1d, 5d, 20d, 60d)
- Volatility measures
- Moving average distances
- Volume profile features
- Momentum indicators

**Fundamental features** (`fundamental_features.py`):
- Valuation ratios (P/E, P/B, EV/EBITDA)
- Profitability metrics (ROE, OPM)
- Growth rates
- Leverage (debt-to-equity)

**Alternative features** (`alternative_features.py`):
- Insider buying/selling signals
- Institutional flow indicators
- Sentiment scores

## Models (`models/`)

### XGBoost (`xgboost_model.py`)
Gradient boosted decision trees. Excels at tabular data with mixed feature types. Handles missing values natively. Produces feature importance rankings for interpretability.

### LSTM (`lstm_model.py`)
Long Short-Term Memory neural network (PyTorch). Processes sequential data — it sees the _order_ of features over time, capturing trends and momentum patterns that tree-based models miss.

### Ensemble (`ensemble.py`)
Combines XGBoost and LSTM predictions:
- Weighted average based on recent out-of-sample accuracy
- Calibrated confidence — when the ensemble says 70% confident, it should be right approximately 70% of the time

### Model Registry (`registry.py`)
Tracks model versions with metadata:
- Training date and data range
- Performance metrics (accuracy, Sharpe, calibration)
- Feature set used
- Walk-forward fold details

Old models are retained for comparison. Rollback is possible.

## Safeguards (`safeguards/`)

### Point-in-Time Enforcement (`point_in_time.py`)

```python
validate_point_in_time(features_df, prediction_date=date(2024, 3, 15))
# → PITValidationResult(is_valid=True/False, violations=[...])

enforce_point_in_time(features_df, prediction_date, strict=True)
# strict=True → raises LookaheadBiasError if any future data found
# strict=False → silently filters out future data
```

This runs on every feature matrix before it reaches a model. There is no way to accidentally train on future data.

### Universe Manager (`universe_manager.py`)

Maintains historical snapshots of which stocks existed at each point in time:

```python
mgr.record_universe(date(2024, 1, 1), ["RELIANCE", "YES_BANK", "DEWAN_HOUSING"])
mgr.record_delisting("DEWAN_HOUSING", date(2024, 6, 1))

# Getting universe as of March 2024 includes DEWAN_HOUSING
# (it was still listed then, even though it's now gone)
snap = mgr.get_universe(date(2024, 3, 1))
# → includes DEWAN_HOUSING

# Bias check on a training set
result = mgr.check_survivorship_bias(
    training_tickers=["RELIANCE"],  # missing DEWAN_HOUSING
    training_start=date(2024, 1, 1),
    training_end=date(2024, 12, 1),
)
# → is_biased=True, delisted_missing=1
```

### Overfitting Detector (`overfitting_detector.py`)

Three independent checks:

**1. Deflated Sharpe Ratio**
If you test 100 strategies, the best one will look good by pure luck. The Deflated Sharpe (Bailey & López de Prado) adjusts the Sharpe ratio for the number of trials. A model needs a higher Sharpe to "earn" significance when many models were tried.

**2. In-Sample vs. Out-of-Sample Ratio**
If a model's Sharpe is 3.0 in-sample but 0.5 out-of-sample (ratio = 6x), it's memorizing training data, not learning patterns. Threshold: ratio > 2x triggers a warning.

**3. Feature Importance Stability**
If the top 10 most important features change completely across cross-validation folds, the model is latching onto noise. Stability is measured as the overlap of top-k features between folds (0 = no overlap, 1 = identical).

Two or more warnings → `is_overfitting = True`, model is flagged for review.

## Training (`training/`)

### Walk-Forward Validation (`walk_forward.py`)

Standard cross-validation doesn't work for time series — you can't validate on data that precedes training data. Walk-forward validation respects temporal ordering:

```
Fold 1: Train [Jan-Jun 2022]  → Validate [Jul-Sep 2022]  → Test [Oct-Dec 2022]
Fold 2: Train [Apr-Sep 2022]  → Validate [Oct-Dec 2022]  → Test [Jan-Mar 2023]
Fold 3: Train [Jul-Dec 2022]  → Validate [Jan-Mar 2023]  → Test [Apr-Jun 2023]
```

Each fold trains on past data only and validates on future data. This gives a realistic estimate of how the model will perform on truly unseen data.

## Evaluation (`evaluation/`)

### Calibration (`calibration.py`)
Groups predictions into buckets (0-10%, 10-20%, ..., 90-100%) and compares predicted probability to actual outcome rate. A well-calibrated model has ECE (Expected Calibration Error) < 10%.

### Attribution (`attribution.py`)
Analyzes which features drive predictions and groups them by category (technical, fundamental, alternative). If 80% of predictive power comes from just RSI and MACD, the model isn't adding value beyond simple technical analysis.

## Key Files

| File | Purpose |
|------|---------|
| `features/pipeline.py` | Orchestrates feature building with PIT enforcement |
| `models/xgboost_model.py` | XGBoost classifier/regressor |
| `models/lstm_model.py` | PyTorch LSTM for sequential patterns |
| `models/ensemble.py` | Weighted model combination |
| `safeguards/point_in_time.py` | Lookahead bias prevention |
| `safeguards/universe_manager.py` | Survivorship bias prevention |
| `safeguards/overfitting_detector.py` | Deflated Sharpe, IS/OOS ratio, feature stability |
| `training/walk_forward.py` | Time-respecting cross-validation |
| `evaluation/calibration.py` | Probability calibration assessment |
