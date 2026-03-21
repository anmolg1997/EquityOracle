"""Pure domain models for the Market Data bounded context.

No external imports beyond stdlib + core types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.core.types import DataQualityFlag, Exchange, Market, Ticker


@dataclass(frozen=True)
class OHLCV:
    ticker: Ticker
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Decimal | None = None
    data_quality: DataQualityFlag = DataQualityFlag.OK
    available_at: datetime | None = None  # point-in-time: when this data became available

    @property
    def typical_price(self) -> Decimal:
        return (self.high + self.low + self.close) / 3

    @property
    def daily_return_pct(self) -> Decimal | None:
        if self.open == 0:
            return None
        return ((self.close - self.open) / self.open) * 100

    @property
    def daily_value(self) -> Decimal:
        return self.close * self.volume


@dataclass(frozen=True)
class FundamentalData:
    ticker: Ticker
    as_of_date: date
    market_cap: Decimal | None = None
    pe_ratio: Decimal | None = None
    pb_ratio: Decimal | None = None
    ev_ebitda: Decimal | None = None
    roe: Decimal | None = None
    roce: Decimal | None = None
    debt_to_equity: Decimal | None = None
    revenue_growth_3yr: Decimal | None = None
    profit_growth_3yr: Decimal | None = None
    operating_profit_margin: Decimal | None = None
    dividend_yield: Decimal | None = None
    eps: Decimal | None = None
    book_value: Decimal | None = None
    promoter_holding_pct: Decimal | None = None
    sector: str = ""
    industry: str = ""
    available_at: datetime | None = None


@dataclass(frozen=True)
class InsiderDeal:
    ticker: Ticker
    deal_date: date
    deal_type: str  # "bulk", "block", "promoter_increase", "promoter_decrease"
    party_name: str
    quantity: int
    price: Decimal
    value: Decimal
    pct_of_equity: Decimal | None = None
    available_at: datetime | None = None


@dataclass(frozen=True)
class InstitutionalFlow:
    market: Market
    date: date
    fii_buy_value: Decimal = Decimal(0)
    fii_sell_value: Decimal = Decimal(0)
    dii_buy_value: Decimal = Decimal(0)
    dii_sell_value: Decimal = Decimal(0)

    @property
    def fii_net(self) -> Decimal:
        return self.fii_buy_value - self.fii_sell_value

    @property
    def dii_net(self) -> Decimal:
        return self.dii_buy_value - self.dii_sell_value

    @property
    def total_net(self) -> Decimal:
        return self.fii_net + self.dii_net


@dataclass(frozen=True)
class MarketBreadth:
    market: Market
    date: date
    advances: int = 0
    declines: int = 0
    unchanged: int = 0
    new_52w_highs: int = 0
    new_52w_lows: int = 0
    above_50_dma_pct: Decimal = Decimal(0)
    above_200_dma_pct: Decimal = Decimal(0)

    @property
    def advance_decline_ratio(self) -> Decimal:
        if self.declines == 0:
            return Decimal("999")
        return Decimal(self.advances) / Decimal(self.declines)

    @property
    def breadth_thrust(self) -> bool:
        total = self.advances + self.declines + self.unchanged
        if total == 0:
            return False
        return (Decimal(self.advances) / Decimal(total)) > Decimal("0.75")


@dataclass
class LiquidityProfile:
    ticker: Ticker
    avg_daily_volume_20d: int = 0
    avg_daily_value_20d: Decimal = Decimal(0)
    market_cap_category: str = "unknown"  # "large", "mid", "small", "micro"
    liquidity_score: Decimal = Decimal(0)  # 0-100

    @property
    def is_tradeable(self) -> bool:
        return self.avg_daily_value_20d > 0


@dataclass
class DataProviderHealth:
    provider_name: str
    is_healthy: bool = True
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    avg_latency_ms: float = 0.0
    error_message: str = ""
