"""Model training pipeline — data split, fit, evaluate, register."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.ml.models.registry import ModelRegistry
from app.ml.models.xgboost_model import XGBoostPredictor
from app.ml.safeguards.overfitting_detector import detect_overfitting
from app.ml.safeguards.point_in_time import create_training_labels
from app.ml.training.walk_forward import run_walk_forward_validation

log = get_logger(__name__)


class TrainingPipeline:
    """Orchestrates model training with safeguards."""

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self._registry = registry or ModelRegistry()

    def train_xgboost(
        self,
        features: pd.DataFrame,
        ohlcv_df: pd.DataFrame,
        horizon_days: int = 5,
        horizon_label: str = "1w",
    ) -> dict:
        """Train an XGBoost model with walk-forward validation."""
        direction, future_return = create_training_labels(ohlcv_df, horizon_days)

        # Drop rows with NaN labels
        valid_mask = direction.notna() & future_return.notna()
        X = features[valid_mask].copy()
        y_dir = direction[valid_mask].values
        y_ret = future_return[valid_mask].values

        # Remove non-numeric columns
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        X = X[numeric_cols].fillna(0)

        if len(X) < 300:
            return {"status": "insufficient_data", "samples": len(X)}

        # Walk-forward validation
        wf_result = run_walk_forward_validation(
            X=X,
            y_direction=y_dir,
            y_return=y_ret,
            model_factory=lambda: XGBoostPredictor(horizon=horizon_label),
            n_folds=5,
        )

        # Overfitting check
        overfit_report = detect_overfitting(
            in_sample_sharpe=wf_result.in_sample_sharpe,
            out_of_sample_sharpe=wf_result.out_of_sample_sharpe,
            n_trials=1,
        )

        if overfit_report.is_overfitting:
            log.warning("overfitting_detected", warnings=overfit_report.warnings)
            return {
                "status": "rejected_overfitting",
                "overfit_report": {
                    "deflated_sharpe": overfit_report.deflated_sharpe,
                    "is_oos_ratio": overfit_report.is_oos_ratio,
                    "warnings": overfit_report.warnings,
                },
            }

        # Train final model on full dataset
        final_model = XGBoostPredictor(horizon=horizon_label)
        train_metrics = final_model.train(X, y_dir, y_ret)

        # Register
        version = self._registry.register(
            model_type="xgboost",
            horizon=horizon_label,
            validation_metrics=wf_result.avg_metrics,
            feature_count=len(numeric_cols),
            training_window=f"{X.index[0]} to {X.index[-1]}",
        )

        final_model.save(Path(version.path))

        return {
            "status": "success",
            "version": version.version,
            "train_metrics": train_metrics,
            "validation_metrics": wf_result.avg_metrics,
            "overfit_check": {
                "deflated_sharpe": overfit_report.deflated_sharpe,
                "is_oos_ratio": overfit_report.is_oos_ratio,
            },
        }
