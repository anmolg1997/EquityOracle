"""Market data repository — SQLAlchemy implementation."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import Exchange, Market, Ticker
from app.domain.market_data.models import (
    FundamentalData,
    InsiderDeal,
    InstitutionalFlow,
    LiquidityProfile,
    MarketBreadth,
    OHLCV,
)
from app.domain.market_data.ports import MarketDataRepository
from app.infrastructure.persistence.models import (
    FundamentalRecord,
    InsiderDealRecord,
    InstitutionalFlowRecord,
    LiquidityProfileRecord,
    MarketBreadthRecord,
    OHLCVRecord,
)


class SQLMarketDataRepository(MarketDataRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_ohlcv_batch(self, records: list[OHLCV]) -> int:
        if not records:
            return 0

        values = [
            {
                "symbol": r.ticker.symbol,
                "exchange": r.ticker.exchange.value,
                "market": r.ticker.market.value,
                "date": r.date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "adjusted_close": r.adjusted_close,
                "data_quality": r.data_quality.value,
                "available_at": r.available_at,
            }
            for r in records
        ]

        stmt = pg_insert(OHLCVRecord).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ohlcv_symbol_exchange_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "adjusted_close": stmt.excluded.adjusted_close,
                "data_quality": stmt.excluded.data_quality,
                "available_at": stmt.excluded.available_at,
            },
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or len(records)

    async def get_ohlcv(self, ticker: Ticker, start: date, end: date) -> list[OHLCV]:
        stmt = (
            select(OHLCVRecord)
            .where(
                and_(
                    OHLCVRecord.symbol == ticker.symbol,
                    OHLCVRecord.exchange == ticker.exchange.value,
                    OHLCVRecord.date >= start,
                    OHLCVRecord.date <= end,
                )
            )
            .order_by(OHLCVRecord.date)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_row_to_ohlcv(r, ticker) for r in rows]

    async def get_latest_ohlcv(self, ticker: Ticker) -> OHLCV | None:
        stmt = (
            select(OHLCVRecord)
            .where(
                and_(
                    OHLCVRecord.symbol == ticker.symbol,
                    OHLCVRecord.exchange == ticker.exchange.value,
                )
            )
            .order_by(OHLCVRecord.date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _row_to_ohlcv(row, ticker) if row else None

    async def save_fundamentals(self, data: FundamentalData) -> None:
        stmt = pg_insert(FundamentalRecord).values(
            symbol=data.ticker.symbol,
            exchange=data.ticker.exchange.value,
            as_of_date=data.as_of_date,
            market_cap=data.market_cap,
            pe_ratio=data.pe_ratio,
            pb_ratio=data.pb_ratio,
            ev_ebitda=data.ev_ebitda,
            roe=data.roe,
            debt_to_equity=data.debt_to_equity,
            revenue_growth_3yr=data.revenue_growth_3yr,
            profit_growth_3yr=data.profit_growth_3yr,
            operating_profit_margin=data.operating_profit_margin,
            dividend_yield=data.dividend_yield,
            eps=data.eps,
            book_value=data.book_value,
            sector=data.sector,
            industry=data.industry,
            available_at=data.available_at,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fundamental_symbol_date",
            set_={"market_cap": stmt.excluded.market_cap, "pe_ratio": stmt.excluded.pe_ratio},
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_fundamentals(self, ticker: Ticker) -> FundamentalData | None:
        stmt = (
            select(FundamentalRecord)
            .where(
                and_(
                    FundamentalRecord.symbol == ticker.symbol,
                    FundamentalRecord.exchange == ticker.exchange.value,
                )
            )
            .order_by(FundamentalRecord.as_of_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        if not row:
            return None
        return FundamentalData(
            ticker=ticker,
            as_of_date=row.as_of_date,
            market_cap=row.market_cap,
            pe_ratio=row.pe_ratio,
            pb_ratio=row.pb_ratio,
            ev_ebitda=row.ev_ebitda,
            roe=row.roe,
            debt_to_equity=row.debt_to_equity,
            revenue_growth_3yr=row.revenue_growth_3yr,
            profit_growth_3yr=row.profit_growth_3yr,
            operating_profit_margin=row.operating_profit_margin,
            dividend_yield=row.dividend_yield,
            eps=row.eps,
            book_value=row.book_value,
            sector=row.sector,
            industry=row.industry,
            available_at=row.available_at,
        )

    async def save_insider_deals(self, deals: list[InsiderDeal]) -> int:
        if not deals:
            return 0
        for d in deals:
            self._session.add(InsiderDealRecord(
                symbol=d.ticker.symbol,
                exchange=d.ticker.exchange.value,
                deal_date=d.deal_date,
                deal_type=d.deal_type,
                party_name=d.party_name,
                quantity=d.quantity,
                price=d.price,
                value=d.value,
                pct_of_equity=d.pct_of_equity,
                available_at=d.available_at,
            ))
        await self._session.commit()
        return len(deals)

    async def save_institutional_flows(self, flows: list[InstitutionalFlow]) -> int:
        if not flows:
            return 0
        for f in flows:
            stmt = pg_insert(InstitutionalFlowRecord).values(
                market=f.market.value,
                date=f.date,
                fii_buy_value=f.fii_buy_value,
                fii_sell_value=f.fii_sell_value,
                dii_buy_value=f.dii_buy_value,
                dii_sell_value=f.dii_sell_value,
            ).on_conflict_do_nothing(constraint="uq_flow_market_date")
            await self._session.execute(stmt)
        await self._session.commit()
        return len(flows)

    async def get_institutional_flows(self, market: Market, days: int) -> list[InstitutionalFlow]:
        cutoff = date.today() - timedelta(days=days)
        stmt = (
            select(InstitutionalFlowRecord)
            .where(
                and_(
                    InstitutionalFlowRecord.market == market.value,
                    InstitutionalFlowRecord.date >= cutoff,
                )
            )
            .order_by(InstitutionalFlowRecord.date.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            InstitutionalFlow(
                market=Market(r.market),
                date=r.date,
                fii_buy_value=r.fii_buy_value,
                fii_sell_value=r.fii_sell_value,
                dii_buy_value=r.dii_buy_value,
                dii_sell_value=r.dii_sell_value,
            )
            for r in rows
        ]

    async def save_market_breadth(self, breadth: MarketBreadth) -> None:
        stmt = pg_insert(MarketBreadthRecord).values(
            market=breadth.market.value,
            date=breadth.date,
            advances=breadth.advances,
            declines=breadth.declines,
            unchanged=breadth.unchanged,
            new_52w_highs=breadth.new_52w_highs,
            new_52w_lows=breadth.new_52w_lows,
            above_50_dma_pct=breadth.above_50_dma_pct,
            above_200_dma_pct=breadth.above_200_dma_pct,
        ).on_conflict_do_nothing(constraint="uq_breadth_market_date")
        await self._session.execute(stmt)
        await self._session.commit()

    async def save_liquidity_profile(self, profile: LiquidityProfile) -> None:
        stmt = pg_insert(LiquidityProfileRecord).values(
            symbol=profile.ticker.symbol,
            exchange=profile.ticker.exchange.value,
            avg_daily_volume_20d=profile.avg_daily_volume_20d,
            avg_daily_value_20d=profile.avg_daily_value_20d,
            market_cap_category=profile.market_cap_category,
            liquidity_score=profile.liquidity_score,
            updated_at=datetime.utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_liquidity_symbol_exchange",
            set_={
                "avg_daily_volume_20d": stmt.excluded.avg_daily_volume_20d,
                "avg_daily_value_20d": stmt.excluded.avg_daily_value_20d,
                "market_cap_category": stmt.excluded.market_cap_category,
                "liquidity_score": stmt.excluded.liquidity_score,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_liquidity_profile(self, ticker: Ticker) -> LiquidityProfile | None:
        stmt = select(LiquidityProfileRecord).where(
            and_(
                LiquidityProfileRecord.symbol == ticker.symbol,
                LiquidityProfileRecord.exchange == ticker.exchange.value,
            )
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        if not row:
            return None
        return LiquidityProfile(
            ticker=ticker,
            avg_daily_volume_20d=row.avg_daily_volume_20d,
            avg_daily_value_20d=row.avg_daily_value_20d,
            market_cap_category=row.market_cap_category,
            liquidity_score=row.liquidity_score,
        )

    async def get_universe(self, market: Market) -> list[Ticker]:
        stmt = (
            select(OHLCVRecord.symbol, OHLCVRecord.exchange)
            .where(OHLCVRecord.market == market.value)
            .distinct()
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        return [
            Ticker(symbol=r[0], exchange=Exchange(r[1]), market=market)
            for r in rows
        ]


def _row_to_ohlcv(row: OHLCVRecord, ticker: Ticker) -> OHLCV:
    from app.core.types import DataQualityFlag
    return OHLCV(
        ticker=ticker,
        date=row.date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        adjusted_close=row.adjusted_close,
        data_quality=DataQualityFlag(row.data_quality),
        available_at=row.available_at,
    )
