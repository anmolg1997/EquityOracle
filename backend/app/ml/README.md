# ML Pipeline

Machine learning for stock return prediction with aggressive safeguards against financial ML pitfalls.

## Structure

```
ml/
├── features/
│   ├── pipeline.py              Feature engineering orchestrator with PIT enforcement
│   ├── technical_features.py    Price-derived features (returns, volatility, MA distances)
│   ├── fundamental_features.py  Accounting-derived features (P/E, ROE, growth)
│   └── alternative_features.py  Insider flows, sentiment, institutional activity
├── models/
│   ├── xgboost_model.py         Gradient boosted classifier/regressor
│   ├── lstm_model.py            PyTorch LSTM for sequential patterns
│   ├── ensemble.py              Weighted model combination
│   └── registry.py              Model versioning with metadata
├── safeguards/
│   ├── point_in_time.py         Lookahead bias prevention (hard enforce)
│   ├── universe_manager.py      Survivorship bias detection
│   └── overfitting_detector.py  Deflated Sharpe, IS/OOS ratio, feature stability
├── training/
│   ├── trainer.py               Model training orchestrator
│   └── walk_forward.py          Time-respecting cross-validation
└── evaluation/
    ├── calibration.py           Probability calibration assessment (ECE)
    └── attribution.py           Feature importance analysis by category
```

## Key Concepts

- **Point-in-time is enforced at the infrastructure level**, not left to individual features. Every data point has an `available_at` timestamp. Features with `available_at` after the prediction date are automatically excluded.
- **Walk-forward validation** respects time ordering: train on past, validate on future, slide window forward. Standard k-fold CV would leak future information.
- **Overfitting detection** uses three independent metrics — Deflated Sharpe, IS/OOS divergence, and feature stability. Two or more warnings flag the model for human review.
- **Calibration** ensures predicted probabilities are reliable. ECE < 0.10 means when the model says "70% confident," it's right approximately 70% of the time.
