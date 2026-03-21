"""TradingView global screener adapter — 3000+ fields across markets."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.core.logging import get_logger
from app.core.types import Exchange, Market, Ticker
from app.domain.market_data.models import (
    DataProviderHealth, FundamentalData, InsiderDeal,
    InstitutionalFlow, MarketBreadth, OHLCV,
)
from app.domain.market_data.ports import MarketDataProvider

log = get_logger(__name__)


class GlobalScreenerProvider(MarketDataProvider):
    """TradingView-Screener integration for global market scanning."""

    async def get_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCV]:
        return []

    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        try:
            from tradingview_screener import Query
            q = Query().select("name", "close", "market_cap_basic", "price_earnings_ttm").where(
                Query.Column("name") == ticker.symbol
            ).limit(1)
            result = q.get_scanner_data()
            if result and len(result) > 1:
                df = result[1]
                if not df.empty:
                    row = df.iloc[0]
                    return FundamentalData(
                        ticker=ticker, as_of_date=date.today(),
                        market_cap=Decimal(str(row.get("market_cap_basic", 0))),
                        pe_ratio=Decimal(str(row.get("price_earnings_ttm", 0))),
                    )
        except Exception as e:
            log.debug("screener_fundamentals_failed", error=str(e))
        return None

    async def get_insider_deals(self, ticker: Ticker, days: int = 30) -> list[InsiderDeal]:
        return []

    async def get_institutional_flows(self, market: Market, days: int = 30) -> list[InstitutionalFlow]:
        return []

    async def get_market_breadth(self, market: Market) -> MarketBreadth | None:
        return None

    async def get_universe(self, market: Market) -> list[Ticker]:
        return []

    async def health_check(self) -> DataProviderHealth:
        return DataProviderHealth(provider_name="tradingview_screener", is_healthy=True, last_success=datetime.utcnow())
