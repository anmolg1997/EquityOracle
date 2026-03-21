"""Application configuration — Pydantic Settings with env + YAML merge."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"


def _load_yaml(filename: str) -> dict[str, Any]:
    path = _CONFIGS_DIR / filename
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    db: str = "equityoracle"
    user: str = "equityoracle"
    password: str = "changeme"

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class LLMSettings(BaseSettings):
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    daily_budget_inr: float = 50.0
    default_provider: str = "gemini"

    model_config = SettingsConfigDict(env_prefix="LLM_")


class MarketDataSettings(BaseSettings):
    alpha_vantage_api_key: str = ""
    newsapi_key: str = ""
    default_market: str = "india"
    min_liquidity_inr: float = 1_000_000.0  # Rs 10L
    min_liquidity_usd: float = 100_000.0

    model_config = SettingsConfigDict(env_prefix="")


class RiskSettings(BaseSettings):
    max_position_pct: float = 0.10
    max_sector_pct: float = 0.30
    max_drawdown_amber: float = 0.08
    max_drawdown_red: float = 0.12
    max_drawdown_black: float = 0.15
    accuracy_amber_threshold: float = 0.40
    accuracy_red_threshold: float = 0.35
    accuracy_window_amber: int = 5
    accuracy_window_red: int = 10

    model_config = SettingsConfigDict(env_prefix="RISK_")


class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"
    default_market: str = "india"

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    market_data: MarketDataSettings = Field(default_factory=MarketDataSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_market_config(self, market: str) -> dict[str, Any]:
        return _load_yaml(f"markets/{market}.yaml")

    def get_risk_config(self) -> dict[str, Any]:
        return _load_yaml("risk.yaml")

    def get_composite_weights(self) -> dict[str, float]:
        data = _load_yaml("composite_weights.yaml")
        return data.get("weights", {
            "technical": 0.25,
            "fundamental": 0.25,
            "sentiment": 0.20,
            "ml_prediction": 0.30,
        })


settings = Settings()
