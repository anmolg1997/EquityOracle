"""Shared value objects used across domain boundaries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import NewType

CorrelationId = NewType("CorrelationId", str)


def new_correlation_id() -> CorrelationId:
    return CorrelationId(uuid.uuid4().hex[:16])


class Market(str, Enum):
    INDIA = "india"
    US = "us"
    GLOBAL = "global"


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"


class TimeHorizon(str, Enum):
    DAY_1 = "1d"
    DAY_3 = "3d"
    WEEK_1 = "1w"
    MONTH_1 = "1m"
    MONTH_3 = "3m"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    UNCERTAIN = "uncertain"


class AutonomyLevel(str, Enum):
    MANUAL = "manual"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


class CircuitBreakerState(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    BLACK = "black"


class DataQualityFlag(str, Enum):
    OK = "ok"
    STALE = "stale"
    SPLIT_SUSPECTED = "split_suspected"
    OUTLIER = "outlier"
    DIVERGENT = "divergent"
    DELISTED = "delisted"


@dataclass(frozen=True)
class Ticker:
    symbol: str
    exchange: Exchange
    market: Market

    @property
    def yfinance_symbol(self) -> str:
        suffix_map = {
            Exchange.NSE: ".NS",
            Exchange.BSE: ".BO",
            Exchange.NYSE: "",
            Exchange.NASDAQ: "",
        }
        return f"{self.symbol}{suffix_map.get(self.exchange, '')}"

    def __str__(self) -> str:
        return f"{self.symbol}:{self.exchange.value}"


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"start {self.start} must be <= end {self.end}")


@dataclass
class PipelineRunContext:
    """Tracks a single pipeline execution from ingestion through recommendations."""

    correlation_id: CorrelationId = field(default_factory=new_correlation_id)
    run_date: date = field(default_factory=date.today)
    started_at: datetime = field(default_factory=datetime.utcnow)
    market: Market = Market.INDIA
