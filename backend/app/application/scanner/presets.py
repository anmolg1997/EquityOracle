"""Pre-built scanner presets loaded from YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.application.scanner.filter_spec import FilterSpec

_PRESETS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "configs" / "scanners"


def load_preset(name: str) -> FilterSpec:
    path = _PRESETS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scanner preset '{name}' not found at {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    spec = FilterSpec(
        name=data.get("name", name),
        description=data.get("description", ""),
    )

    for filt in data.get("filters", []):
        spec.add(
            field_name=filt["field"],
            operator=filt["operator"],
            value=filt.get("value"),
            reference=filt.get("reference"),
            min=filt.get("min"),
            max=filt.get("max"),
            multiplier=filt.get("multiplier", 1.0),
            periods=filt.get("periods", 0),
        )

    return spec


def list_presets() -> list[dict[str, str]]:
    presets: list[dict[str, str]] = []
    if not _PRESETS_DIR.exists():
        return presets

    for p in sorted(_PRESETS_DIR.glob("*.yaml")):
        with open(p) as f:
            data = yaml.safe_load(f)
        presets.append({
            "id": p.stem,
            "name": data.get("name", p.stem),
            "description": data.get("description", ""),
        })
    return presets
