"""US market data provider — yfinance + Alpha Vantage adapter."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import yfinance as yf

from app.core.logging import get_logger
from app.core.types import Exchange, Market, Ticker
from app.domain.market_data.models import (
    DataProviderHealth,
    FundamentalData,
    InsiderDeal,
    InstitutionalFlow,
    MarketBreadth,
    OHLCV,
)
from app.domain.market_data.ports import MarketDataProvider

log = get_logger(__name__)


class USDataProvider(MarketDataProvider):
    """US market data provider using yfinance."""

    async def get_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCV]:
        try:
            yf_ticker = yf.Ticker(ticker.symbol)
            df = yf_ticker.history(start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), auto_adjust=False)
            if df.empty:
                return []

            records: list[OHLCV] = []
            for idx, row in df.iterrows():
                record_date = idx.date() if hasattr(idx, "date") else idx
                records.append(OHLCV(
                    ticker=ticker, date=record_date,
                    open=Decimal(str(round(row["Open"], 2))),
                    high=Decimal(str(round(row["High"], 2))),
                    low=Decimal(str(round(row["Low"], 2))),
                    close=Decimal(str(round(row["Close"], 2))),
                    volume=int(row.get("Volume", 0)),
                    available_at=datetime.combine(record_date, datetime.min.time()) + timedelta(hours=16),
                ))
            return records
        except Exception as e:
            log.error("us_ohlcv_failed", ticker=str(ticker), error=str(e))
            raise

    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        try:
            info = yf.Ticker(ticker.symbol).info
            if not info:
                return None
            return FundamentalData(
                ticker=ticker, as_of_date=date.today(),
                market_cap=_dec(info.get("marketCap")),
                pe_ratio=_dec(info.get("trailingPE")),
                pb_ratio=_dec(info.get("priceToBook")),
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
            )
        except Exception:
            return None

    async def get_insider_deals(self, ticker: Ticker, days: int = 30) -> list[InsiderDeal]:
        return []

    async def get_institutional_flows(self, market: Market, days: int = 30) -> list[InstitutionalFlow]:
        return []

    async def get_market_breadth(self, market: Market) -> MarketBreadth | None:
        return MarketBreadth(market=market, date=date.today())

    async def get_universe(self, market: Market) -> list[Ticker]:
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V",
                    "JNJ", "UNH", "XOM", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY",
                    "COST", "PEP", "KO", "AVGO", "WMT", "ADBE", "TMO", "CSCO", "MCD", "CRM"]
        return [Ticker(symbol=s, exchange=Exchange.NYSE, market=Market.US) for s in symbols]

    async def health_check(self) -> DataProviderHealth:
        try:
            yf.Ticker("AAPL").info
            return DataProviderHealth(provider_name="us_yfinance", is_healthy=True, last_success=datetime.utcnow())
        except Exception as e:
            return DataProviderHealth(provider_name="us_yfinance", is_healthy=False, error_message=str(e))


def _dec(val) -> Decimal | None:
    return Decimal(str(val)) if val is not None else None
