"""LSTM model for sequence-based return prediction using PyTorch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from app.core.logging import get_logger

log = get_logger(__name__)


class LSTMNetwork(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True,
        )
        self.direction_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        self.return_head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]
        direction = self.direction_head(last_hidden)
        expected_return = self.return_head(last_hidden)
        return direction, expected_return


@dataclass
class LSTMPrediction:
    expected_return: float
    direction_probability: float
    confidence: float


class LSTMPredictor:
    """LSTM-based predictor using 60-day feature windows."""

    def __init__(
        self,
        input_size: int = 50,
        hidden_size: int = 64,
        sequence_length: int = 60,
        horizon: str = "1w",
    ) -> None:
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.sequence_length = sequence_length
        self.horizon = horizon
        self._model: LSTMNetwork | None = None
        self._is_fitted = False
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def train(
        self,
        X_sequences: np.ndarray,
        y_direction: np.ndarray,
        y_return: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        lr: float = 0.001,
    ) -> dict:
        """Train the LSTM model.

        X_sequences: shape (n_samples, sequence_length, n_features)
        """
        self.input_size = X_sequences.shape[2]
        self._model = LSTMNetwork(self.input_size, self.hidden_size).to(self._device)

        optimizer = torch.optim.Adam(self._model.parameters(), lr=lr)
        dir_criterion = nn.BCELoss()
        ret_criterion = nn.MSELoss()

        X_tensor = torch.FloatTensor(X_sequences).to(self._device)
        y_dir_tensor = torch.FloatTensor(y_direction).unsqueeze(1).to(self._device)
        y_ret_tensor = torch.FloatTensor(y_return).unsqueeze(1).to(self._device)

        dataset = torch.utils.data.TensorDataset(X_tensor, y_dir_tensor, y_ret_tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

        self._model.train()
        final_loss = 0.0

        for epoch in range(epochs):
            epoch_loss = 0.0
            for X_batch, y_dir_batch, y_ret_batch in loader:
                optimizer.zero_grad()
                dir_pred, ret_pred = self._model(X_batch)
                loss = dir_criterion(dir_pred, y_dir_batch) + ret_criterion(ret_pred, y_ret_batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            final_loss = epoch_loss / len(loader)

        self._is_fitted = True
        return {"final_loss": final_loss, "epochs": epochs, "samples": len(X_sequences)}

    def predict(self, X_sequences: np.ndarray, n_mc_samples: int = 10) -> list[LSTMPrediction]:
        """Predict with optional Monte Carlo dropout for uncertainty estimation."""
        if not self._is_fitted or self._model is None:
            raise RuntimeError("Model not trained")

        X_tensor = torch.FloatTensor(X_sequences).to(self._device)

        # MC Dropout: run multiple forward passes with dropout enabled
        self._model.train()  # keep dropout active
        dir_samples = []
        ret_samples = []

        with torch.no_grad():
            for _ in range(n_mc_samples):
                dir_pred, ret_pred = self._model(X_tensor)
                dir_samples.append(dir_pred.cpu().numpy())
                ret_samples.append(ret_pred.cpu().numpy())

        dir_mean = np.mean(dir_samples, axis=0)
        ret_mean = np.mean(ret_samples, axis=0)
        dir_std = np.std(dir_samples, axis=0)

        results: list[LSTMPrediction] = []
        for i in range(len(X_sequences)):
            confidence = max(0, 1 - float(dir_std[i][0]) * 4)  # higher std = lower confidence
            results.append(LSTMPrediction(
                expected_return=float(ret_mean[i][0]),
                direction_probability=float(dir_mean[i][0]),
                confidence=confidence,
            ))

        return results

    def save(self, path: Path) -> None:
        if self._model:
            path.mkdir(parents=True, exist_ok=True)
            torch.save(self._model.state_dict(), path / f"lstm_{self.horizon}.pt")

    def load(self, path: Path) -> None:
        self._model = LSTMNetwork(self.input_size, self.hidden_size).to(self._device)
        self._model.load_state_dict(torch.load(path / f"lstm_{self.horizon}.pt", map_location=self._device))
        self._is_fitted = True
