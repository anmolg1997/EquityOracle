"""Walk-forward cross-validation for time-series ML models."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class WalkForwardFold:
    fold_index: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    metrics: dict = field(default_factory=dict)


@dataclass
class WalkForwardResult:
    folds: list[WalkForwardFold]
    avg_metrics: dict = field(default_factory=dict)
    in_sample_sharpe: float = 0.0
    out_of_sample_sharpe: float = 0.0


def walk_forward_split(
    n_samples: int,
    n_folds: int = 5,
    min_train_size: int = 252,
    test_size: int = 63,
) -> list[tuple[range, range]]:
    """Generate walk-forward train/test splits.

    Unlike k-fold, walk-forward preserves temporal ordering:
    - Train on months 1..N
    - Test on month N+1
    - Roll forward
    """
    splits: list[tuple[range, range]] = []

    for i in range(n_folds):
        train_end = min_train_size + i * test_size
        test_end = train_end + test_size

        if test_end > n_samples:
            break

        train_range = range(0, train_end)
        test_range = range(train_end, test_end)
        splits.append((train_range, test_range))

    return splits


def run_walk_forward_validation(
    X: pd.DataFrame,
    y_direction: np.ndarray,
    y_return: np.ndarray,
    model_factory,
    n_folds: int = 5,
    min_train_size: int = 252,
    test_size: int = 63,
) -> WalkForwardResult:
    """Run walk-forward validation and return aggregated metrics."""
    splits = walk_forward_split(len(X), n_folds, min_train_size, test_size)

    folds: list[WalkForwardFold] = []
    all_is_sharpes: list[float] = []
    all_oos_sharpes: list[float] = []

    for i, (train_idx, test_idx) in enumerate(splits):
        X_train = X.iloc[list(train_idx)]
        X_test = X.iloc[list(test_idx)]
        y_dir_train = y_direction[list(train_idx)]
        y_dir_test = y_direction[list(test_idx)]
        y_ret_train = y_return[list(train_idx)]
        y_ret_test = y_return[list(test_idx)]

        model = model_factory()
        model.train(X_train, y_dir_train, y_ret_train)

        predictions = model.predict(X_test)

        pred_returns = np.array([p.expected_return for p in predictions])
        direction_accuracy = np.mean(
            [1 if (p.direction_probability > 0.5) == (y_dir_test[j] == 1) else 0
             for j, p in enumerate(predictions)]
        )

        is_sharpe = _compute_sharpe(y_ret_train)
        oos_sharpe = _compute_sharpe(pred_returns)
        all_is_sharpes.append(is_sharpe)
        all_oos_sharpes.append(oos_sharpe)

        fold = WalkForwardFold(
            fold_index=i,
            train_start=train_idx.start,
            train_end=train_idx.stop,
            test_start=test_idx.start,
            test_end=test_idx.stop,
            metrics={
                "direction_accuracy": float(direction_accuracy),
                "is_sharpe": is_sharpe,
                "oos_sharpe": oos_sharpe,
            },
        )
        folds.append(fold)
        log.info("walk_forward_fold", fold=i, accuracy=f"{direction_accuracy:.3f}")

    avg_metrics = {}
    if folds:
        for key in folds[0].metrics:
            avg_metrics[key] = float(np.mean([f.metrics[key] for f in folds]))

    return WalkForwardResult(
        folds=folds,
        avg_metrics=avg_metrics,
        in_sample_sharpe=float(np.mean(all_is_sharpes)) if all_is_sharpes else 0,
        out_of_sample_sharpe=float(np.mean(all_oos_sharpes)) if all_oos_sharpes else 0,
    )


def _compute_sharpe(returns: np.ndarray, risk_free: float = 0.0) -> float:
    if len(returns) == 0:
        return 0.0
    excess = returns - risk_free / 252
    std = np.std(excess)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(252))
