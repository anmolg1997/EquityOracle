"""XGBoost model for equity return prediction."""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier, XGBRegressor

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class XGBoostPrediction:
    expected_return: float
    direction_probability: float  # probability of positive return
    confidence: float
    feature_importance: dict[str, float] = field(default_factory=dict)


class XGBoostPredictor:
    """XGBoost-based return predictor: classification (direction) + regression (magnitude)."""

    def __init__(self, horizon: str = "1w") -> None:
        self.horizon = horizon
        self._classifier = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
        )
        self._regressor = XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            random_state=42,
        )
        self._is_fitted = False
        self._feature_names: list[str] = []

    def train(self, X: pd.DataFrame, y_direction: np.ndarray, y_return: np.ndarray) -> dict:
        """Train both classifier and regressor."""
        self._feature_names = list(X.columns)

        X_clean = X.fillna(0)

        self._classifier.fit(X_clean, y_direction)
        self._regressor.fit(X_clean, y_return)
        self._is_fitted = True

        direction_score = self._classifier.score(X_clean, y_direction)

        return {
            "direction_accuracy": direction_score,
            "feature_count": len(self._feature_names),
            "samples": len(X),
        }

    def predict(self, X: pd.DataFrame) -> list[XGBoostPrediction]:
        if not self._is_fitted:
            raise RuntimeError("Model not trained")

        X_clean = X.fillna(0)
        if list(X_clean.columns) != self._feature_names:
            X_clean = X_clean.reindex(columns=self._feature_names, fill_value=0)

        dir_proba = self._classifier.predict_proba(X_clean)
        ret_pred = self._regressor.predict(X_clean)

        importance = dict(zip(
            self._feature_names,
            [float(v) for v in self._classifier.feature_importances_],
        ))

        results: list[XGBoostPrediction] = []
        for i in range(len(X_clean)):
            pos_prob = float(dir_proba[i][1]) if dir_proba.shape[1] > 1 else float(dir_proba[i][0])
            confidence = abs(pos_prob - 0.5) * 2  # 0 when uncertain, 1 when certain

            results.append(XGBoostPrediction(
                expected_return=float(ret_pred[i]),
                direction_probability=pos_prob,
                confidence=confidence,
                feature_importance=importance,
            ))

        return results

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        with open(path / f"xgb_{self.horizon}_clf.pkl", "wb") as f:
            pickle.dump(self._classifier, f)
        with open(path / f"xgb_{self.horizon}_reg.pkl", "wb") as f:
            pickle.dump(self._regressor, f)
        with open(path / f"xgb_{self.horizon}_meta.pkl", "wb") as f:
            pickle.dump({"feature_names": self._feature_names, "horizon": self.horizon}, f)

    def load(self, path: Path) -> None:
        with open(path / f"xgb_{self.horizon}_clf.pkl", "rb") as f:
            self._classifier = pickle.load(f)
        with open(path / f"xgb_{self.horizon}_reg.pkl", "rb") as f:
            self._regressor = pickle.load(f)
        with open(path / f"xgb_{self.horizon}_meta.pkl", "rb") as f:
            meta = pickle.load(f)
            self._feature_names = meta["feature_names"]
        self._is_fitted = True
