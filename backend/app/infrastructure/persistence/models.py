"""SQLAlchemy ORM models for all database tables."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base


class OHLCVRecord(Base):
    __tablename__ = "ohlcv"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    data_quality: Mapped[str] = mapped_column(String(20), default="ok")
    available_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "date", name="uq_ohlcv_symbol_exchange_date"),
        Index("ix_ohlcv_symbol_date", "symbol", "date"),
        Index("ix_ohlcv_market_date", "market", "date"),
    )


class FundamentalRecord(Base):
    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    pb_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    ev_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    roce: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    revenue_growth_3yr: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    profit_growth_3yr: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    operating_profit_margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    book_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    promoter_holding_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    sector: Mapped[str] = mapped_column(String(100), default="")
    industry: Mapped[str] = mapped_column(String(100), default="")
    available_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", "as_of_date", name="uq_fundamental_symbol_date"),
        Index("ix_fundamentals_symbol", "symbol"),
    )


class InsiderDealRecord(Base):
    __tablename__ = "insider_deals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    deal_date: Mapped[date] = mapped_column(Date, nullable=False)
    deal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    party_name: Mapped[str] = mapped_column(String(200), default="")
    quantity: Mapped[int] = mapped_column(BigInteger, default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    pct_of_equity: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    available_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_insider_symbol_date", "symbol", "deal_date"),)


class InstitutionalFlowRecord(Base):
    __tablename__ = "institutional_flows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    fii_buy_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    fii_sell_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    dii_buy_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    dii_sell_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("market", "date", name="uq_flow_market_date"),
    )


class MarketBreadthRecord(Base):
    __tablename__ = "market_breadth"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    advances: Mapped[int] = mapped_column(Integer, default=0)
    declines: Mapped[int] = mapped_column(Integer, default=0)
    unchanged: Mapped[int] = mapped_column(Integer, default=0)
    new_52w_highs: Mapped[int] = mapped_column(Integer, default=0)
    new_52w_lows: Mapped[int] = mapped_column(Integer, default=0)
    above_50_dma_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    above_200_dma_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("market", "date", name="uq_breadth_market_date"),
    )


class LiquidityProfileRecord(Base):
    __tablename__ = "liquidity_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    avg_daily_volume_20d: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_daily_value_20d: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    market_cap_category: Mapped[str] = mapped_column(String(10), default="unknown")
    liquidity_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_liquidity_symbol_exchange"),
    )


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    correlation_id: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    horizon: Mapped[str] = mapped_column(String(5), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    expected_return_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    composite_score: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    independent_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    exit_strategy: Mapped[str] = mapped_column(Text, default="")
    thesis_summary: Mapped[str] = mapped_column(Text, default="")
    decision_context: Mapped[dict | None] = mapped_column(JSONB)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actual_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    outcome_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_rec_symbol_horizon", "symbol", "horizon"),
        Index("ix_rec_correlation", "correlation_id"),
        Index("ix_rec_predicted_at", "predicted_at"),
    )


class PortfolioPositionRecord(Base):
    __tablename__ = "portfolio_positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    exit_date: Mapped[date | None] = mapped_column(Date)
    gross_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    net_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    transaction_costs: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    slippage_costs: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    estimated_tax: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    recommendation_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_position_portfolio_open", "portfolio_id", "is_open"),
        Index("ix_position_symbol", "symbol"),
    )


class CircuitBreakerLog(Base):
    __tablename__ = "circuit_breaker_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    previous_state: Mapped[str] = mapped_column(String(10), nullable=False)
    new_state: Mapped[str] = mapped_column(String(10), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeightChangeLog(Base):
    __tablename__ = "weight_change_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    old_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    new_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    before_metrics: Mapped[dict | None] = mapped_column(JSONB)
    after_metrics: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProviderHealthLog(Base):
    __tablename__ = "provider_health_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_healthy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    error_message: Mapped[str] = mapped_column(Text, default="")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
