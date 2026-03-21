"""India market data provider — NSELib + yfinance adapter.

Implements MarketDataProvider for NSE/BSE equities.
"""

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

NIFTY_500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"


class IndiaDataProvider(MarketDataProvider):
    """Primary India data provider using yfinance with NSE suffixes.

    Falls back gracefully when nselib or specific endpoints are unavailable.
    """

    def __init__(self) -> None:
        self._last_health_check: datetime | None = None
        self._healthy = True

    async def get_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCV]:
        try:
            yf_ticker = yf.Ticker(ticker.yfinance_symbol)
            df = yf_ticker.history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=False,
            )

            if df.empty:
                log.warning("no_ohlcv_data", ticker=str(ticker), start=str(start), end=str(end))
                return []

            records: list[OHLCV] = []
            for idx, row in df.iterrows():
                record_date = idx.date() if hasattr(idx, "date") else idx
                records.append(
                    OHLCV(
                        ticker=ticker,
                        date=record_date,
                        open=Decimal(str(round(row["Open"], 2))),
                        high=Decimal(str(round(row["High"], 2))),
                        low=Decimal(str(round(row["Low"], 2))),
                        close=Decimal(str(round(row["Close"], 2))),
                        volume=int(row.get("Volume", 0)),
                        adjusted_close=Decimal(str(round(row["Adj Close"], 2))) if "Adj Close" in row else None,
                        available_at=datetime.combine(record_date, datetime.min.time()) + timedelta(hours=15, minutes=30),
                    )
                )
            return records

        except Exception as e:
            log.error("ohlcv_fetch_failed", ticker=str(ticker), error=str(e))
            raise

    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        try:
            yf_ticker = yf.Ticker(ticker.yfinance_symbol)
            info = yf_ticker.info

            if not info or info.get("regularMarketPrice") is None:
                return None

            return FundamentalData(
                ticker=ticker,
                as_of_date=date.today(),
                market_cap=_to_decimal(info.get("marketCap")),
                pe_ratio=_to_decimal(info.get("trailingPE")),
                pb_ratio=_to_decimal(info.get("priceToBook")),
                ev_ebitda=_to_decimal(info.get("enterpriseToEbitda")),
                roe=_to_decimal(info.get("returnOnEquity")),
                debt_to_equity=_to_decimal(info.get("debtToEquity")),
                revenue_growth_3yr=_to_decimal(info.get("revenueGrowth")),
                profit_growth_3yr=_to_decimal(info.get("earningsGrowth")),
                operating_profit_margin=_to_decimal(info.get("operatingMargins")),
                dividend_yield=_to_decimal(info.get("dividendYield")),
                eps=_to_decimal(info.get("trailingEps")),
                book_value=_to_decimal(info.get("bookValue")),
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
                available_at=datetime.utcnow(),
            )
        except Exception as e:
            log.error("fundamentals_fetch_failed", ticker=str(ticker), error=str(e))
            return None

    async def get_insider_deals(self, ticker: Ticker, days: int = 30) -> list[InsiderDeal]:
        # nselib integration for bulk/block deals
        try:
            from nselib import capital_market
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            deals: list[InsiderDeal] = []
            try:
                bulk_data = capital_market.bulk_deal_data()
                if bulk_data is not None and not bulk_data.empty:
                    ticker_deals = bulk_data[
                        bulk_data["Symbol"].str.upper() == ticker.symbol.upper()
                    ] if "Symbol" in bulk_data.columns else bulk_data.head(0)

                    for _, row in ticker_deals.iterrows():
                        try:
                            deals.append(
                                InsiderDeal(
                                    ticker=ticker,
                                    deal_date=date.today(),
                                    deal_type="bulk",
                                    party_name=str(row.get("Client Name", "Unknown")),
                                    quantity=int(row.get("Quantity Traded", 0)),
                                    price=Decimal(str(row.get("Trade Price / Wt. Avg. Price", 0))),
                                    value=Decimal(str(row.get("Quantity Traded", 0))) * Decimal(str(row.get("Trade Price / Wt. Avg. Price", 0))),
                                    available_at=datetime.utcnow(),
                                )
                            )
                        except (ValueError, KeyError):
                            continue
            except Exception:
                log.debug("nselib_bulk_deals_unavailable", ticker=str(ticker))

            return deals

        except ImportError:
            log.warning("nselib_not_available")
            return []
        except Exception as e:
            log.error("insider_deals_failed", ticker=str(ticker), error=str(e))
            return []

    async def get_institutional_flows(self, market: Market, days: int = 30) -> list[InstitutionalFlow]:
        try:
            from nselib import capital_market
            fii_dii = capital_market.fii_dii_trading_activity()
            if fii_dii is None or fii_dii.empty:
                return []

            flows: list[InstitutionalFlow] = []
            for _, row in fii_dii.head(days).iterrows():
                try:
                    flows.append(
                        InstitutionalFlow(
                            market=market,
                            date=date.today(),
                            fii_buy_value=_to_decimal(row.get("FII Buy Value")) or Decimal(0),
                            fii_sell_value=_to_decimal(row.get("FII Sell Value")) or Decimal(0),
                            dii_buy_value=_to_decimal(row.get("DII Buy Value")) or Decimal(0),
                            dii_sell_value=_to_decimal(row.get("DII Sell Value")) or Decimal(0),
                        )
                    )
                except (ValueError, KeyError):
                    continue
            return flows

        except ImportError:
            log.warning("nselib_not_available_for_flows")
            return []
        except Exception as e:
            log.error("institutional_flows_failed", error=str(e))
            return []

    async def get_market_breadth(self, market: Market) -> MarketBreadth | None:
        return MarketBreadth(market=market, date=date.today())

    async def get_universe(self, market: Market) -> list[Ticker]:
        """Return Nifty 500 as the default India universe."""
        try:
            import pandas as pd
            df = pd.read_csv(NIFTY_500_URL)
            tickers: list[Ticker] = []
            symbol_col = "Symbol" if "Symbol" in df.columns else df.columns[2]
            for symbol in df[symbol_col].dropna():
                tickers.append(Ticker(symbol=str(symbol).strip(), exchange=Exchange.NSE, market=Market.INDIA))
            log.info("universe_loaded", market=market.value, count=len(tickers))
            return tickers

        except Exception as e:
            log.error("universe_load_failed", error=str(e))
            return _fallback_universe()

    async def health_check(self) -> DataProviderHealth:
        try:
            test = yf.Ticker("RELIANCE.NS")
            info = test.info
            self._healthy = bool(info and info.get("regularMarketPrice"))
            self._last_health_check = datetime.utcnow()
            return DataProviderHealth(
                provider_name="india_yfinance",
                is_healthy=self._healthy,
                last_success=self._last_health_check if self._healthy else None,
            )
        except Exception as e:
            self._healthy = False
            return DataProviderHealth(
                provider_name="india_yfinance",
                is_healthy=False,
                error_message=str(e),
            )


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _fallback_universe() -> list[Ticker]:
    """Hardcoded fallback of top 50 NSE stocks if CSV download fails."""
    symbols = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
        "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI",
        "SUNPHARMA", "TITAN", "ULTRACEMCO", "NESTLEIND", "WIPRO",
        "HCLTECH", "BAJAJFINSV", "ONGC", "NTPC", "POWERGRID",
        "TATAMOTORS", "TATASTEEL", "JSWSTEEL", "ADANIENT", "ADANIPORTS",
        "TECHM", "DRREDDY", "DIVISLAB", "CIPLA", "COALINDIA",
        "BPCL", "GRASIM", "EICHERMOT", "INDUSINDBK", "HEROMOTOCO",
        "BRITANNIA", "APOLLOHOSP", "SBILIFE", "HDFCLIFE", "BAJAJ-AUTO",
        "M&M", "TATACONSUM", "HINDALCO", "UPL", "SHREECEM",
    ]
    return [Ticker(symbol=s, exchange=Exchange.NSE, market=Market.INDIA) for s in symbols]
