# Analysis Domain

Scores every stock on multiple independent dimensions and combines them into a composite score.

## Files

| File | Purpose |
|------|---------|
| `models.py` | `TechnicalScore`, `FactorScore`, `SentimentScore`, `CompositeScore`, `ScanResult` |
| `technical.py` | Computes 50+ indicators via pandas-ta: RSI, MACD, ADX, Bollinger, ATR, OBV, SMA/EMA, RS rating |
| `factors.py` | Three factor scores (0–100 each): Momentum (6m/12m returns), Quality (profit growth, OPM, ROE), Value (P/E, P/B, EV/EBITDA) |
| `composite.py` | Weighted aggregation of technical + fundamental + sentiment + ML pillars into a 0–100 composite. Classifies confidence (High/Medium/Low) |
| `decorrelation.py` | Pairwise rank correlation between pillars. Down-weights redundant pillars (>0.75 correlation). Reports effective signal count |
| `ports.py` | `AnalysisRepository` abstract interface |

## Key Concepts

- **Decorrelation** prevents double-counting. If technical and momentum scores measure the same thing (rank correlation > 0.75), the redundant one's weight is halved.
- **Factor scoring** handles missing data gracefully — insufficient fundamental data defaults to a neutral 50 score rather than crashing.
- **Composite weights** are loaded from `configs/composite_weights.yaml` and tuned by the self-improvement system.
