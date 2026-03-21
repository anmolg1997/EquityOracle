"""Model registry — versioning, saving, loading trained models."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

_REGISTRY_DIR = Path(__file__).resolve().parent.parent.parent.parent / "model_registry"


@dataclass
class ModelVersion:
    model_type: str
    horizon: str
    version: str
    trained_at: str
    training_window: str
    feature_count: int
    validation_metrics: dict = field(default_factory=dict)
    path: str = ""


class ModelRegistry:
    """Manages model versions — save, load, list, and compare."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or _REGISTRY_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        model_type: str,
        horizon: str,
        validation_metrics: dict,
        feature_count: int = 0,
        training_window: str = "",
    ) -> ModelVersion:
        version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_dir = self._base_dir / model_type / horizon / version
        model_dir.mkdir(parents=True, exist_ok=True)

        v = ModelVersion(
            model_type=model_type,
            horizon=horizon,
            version=version,
            trained_at=datetime.utcnow().isoformat(),
            training_window=training_window,
            feature_count=feature_count,
            validation_metrics=validation_metrics,
            path=str(model_dir),
        )

        with open(model_dir / "metadata.json", "w") as f:
            json.dump(asdict(v), f, indent=2)

        log.info("model_registered", model_type=model_type, horizon=horizon, version=version)
        return v

    def get_latest(self, model_type: str, horizon: str) -> ModelVersion | None:
        model_dir = self._base_dir / model_type / horizon
        if not model_dir.exists():
            return None

        versions = sorted(model_dir.iterdir(), reverse=True)
        for v_dir in versions:
            meta_path = v_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    data = json.load(f)
                return ModelVersion(**data)
        return None

    def list_versions(self, model_type: str, horizon: str) -> list[ModelVersion]:
        model_dir = self._base_dir / model_type / horizon
        if not model_dir.exists():
            return []

        versions: list[ModelVersion] = []
        for v_dir in sorted(model_dir.iterdir(), reverse=True):
            meta_path = v_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    data = json.load(f)
                versions.append(ModelVersion(**data))
        return versions
