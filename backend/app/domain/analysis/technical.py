"""Technical indicator computation — wraps pandas-ta in pure domain interface."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd
import pandas_ta as ta

from app.core.types import Ticker
from app.domain.analysis.models import TechnicalScore
from app.domain.market_data.models import OHLCV


def compute_technical_score(ticker: Ticker, ohlcv: list[OHLCV]) -> TechnicalScore:
    """Compute all technical indicators from OHLCV data.

    Returns a TechnicalScore with all relevant indicators populated.
    Requires at least 200 bars for meaningful results.
    """
    if len(ohlcv) < 20:
        return TechnicalScore(ticker=ticker, as_of_date=date.today())

    df = _ohlcv_to_dataframe(ohlcv)
    as_of = ohlcv[-1].date

    rsi = df.ta.rsi(length=14)
    macd_result = df.ta.macd(fast=12, slow=26, signal=9)
    adx = df.ta.adx(length=14)
    bb = df.ta.bbands(length=20)
    atr = df.ta.atr(length=14)

    sma_20 = df.ta.sma(length=20)
    sma_50 = df.ta.sma(length=50)
    sma_150 = df.ta.sma(length=150) if len(df) >= 150 else None
    sma_200 = df.ta.sma(length=200) if len(df) >= 200 else None
    ema_12 = df.ta.ema(length=12)
    ema_26 = df.ta.ema(length=26)

    obv = df.ta.obv()

    latest = df.iloc[-1]

    # Volume ratio: current volume / 20-day average
    vol_sma = df["volume"].rolling(20).mean()
    volume_ratio = latest["volume"] / vol_sma.iloc[-1] if vol_sma.iloc[-1] > 0 else 1.0

    # Bollinger position (0=lower, 0.5=middle, 1=upper)
    bb_position = None
    if bb is not None and not bb.empty:
        bb_lower_col = [c for c in bb.columns if "BBL" in c]
        bb_upper_col = [c for c in bb.columns if "BBU" in c]
        if bb_lower_col and bb_upper_col:
            bb_lower = bb[bb_lower_col[0]].iloc[-1]
            bb_upper = bb[bb_upper_col[0]].iloc[-1]
            bb_width = bb_upper - bb_lower
            if bb_width > 0:
                bb_position = _dec((latest["close"] - bb_lower) / bb_width)

    # OBV trend
    obv_trend = "flat"
    if obv is not None and len(obv) >= 20:
        obv_sma = obv.rolling(20).mean()
        if obv.iloc[-1] > obv_sma.iloc[-1] * 1.02:
            obv_trend = "up"
        elif obv.iloc[-1] < obv_sma.iloc[-1] * 0.98:
            obv_trend = "down"

    # RS rating — percentile rank of 6-month return
    rs_rating = _compute_rs_rating(df)

    score = _compute_composite_technical_score(
        rsi=_safe_last(rsi),
        macd_hist=_safe_last(macd_result.iloc[:, 2] if macd_result is not None and len(macd_result.columns) >= 3 else None),
        adx_val=_safe_last(adx.iloc[:, 0] if adx is not None else None),
        bb_pos=bb_position,
        volume_ratio=volume_ratio,
        obv_trend=obv_trend,
        rs=rs_rating,
    )

    return TechnicalScore(
        ticker=ticker,
        as_of_date=as_of,
        rsi_14=_safe_dec(rsi),
        macd_signal=_safe_dec(macd_result.iloc[:, 1] if macd_result is not None and len(macd_result.columns) >= 2 else None),
        macd_histogram=_safe_dec(macd_result.iloc[:, 2] if macd_result is not None and len(macd_result.columns) >= 3 else None),
        adx_14=_safe_dec(adx.iloc[:, 0] if adx is not None else None),
        bb_position=bb_position,
        sma_20=_safe_dec(sma_20),
        sma_50=_safe_dec(sma_50),
        sma_150=_safe_dec(sma_150),
        sma_200=_safe_dec(sma_200),
        ema_12=_safe_dec(ema_12),
        ema_26=_safe_dec(ema_26),
        atr_14=_safe_dec(atr),
        volume_ratio=_dec(volume_ratio),
        obv_trend=obv_trend,
        rs_rating=_dec(rs_rating) if rs_rating else None,
        score=score,
    )


def _ohlcv_to_dataframe(ohlcv: list[OHLCV]) -> pd.DataFrame:
    data = {
        "date": [r.date for r in ohlcv],
        "open": [float(r.open) for r in ohlcv],
        "high": [float(r.high) for r in ohlcv],
        "low": [float(r.low) for r in ohlcv],
        "close": [float(r.close) for r in ohlcv],
        "volume": [r.volume for r in ohlcv],
    }
    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    return df


def _compute_rs_rating(df: pd.DataFrame) -> float | None:
    if len(df) < 126:
        return None
    ret_6m = (df["close"].iloc[-1] / df["close"].iloc[-126] - 1) * 100
    return min(max(float(ret_6m) + 50, 0), 99)


def _compute_composite_technical_score(
    rsi: float | None,
    macd_hist: float | None,
    adx_val: float | None,
    bb_pos: Decimal | None,
    volume_ratio: float,
    obv_trend: str,
    rs: float | None,
) -> Decimal:
    score = Decimal(50)

    if rsi is not None:
        if 40 <= rsi <= 60:
            score += Decimal(5)
        elif rsi < 30:
            score += Decimal(10)  # oversold = potential buy
        elif rsi > 70:
            score -= Decimal(5)

    if macd_hist is not None:
        if macd_hist > 0:
            score += Decimal(10)
        else:
            score -= Decimal(5)

    if adx_val is not None and adx_val > 25:
        score += Decimal(5)

    if bb_pos is not None:
        if float(bb_pos) < 0.3:
            score += Decimal(5)

    if volume_ratio > 1.5:
        score += Decimal(5)

    if obv_trend == "up":
        score += Decimal(5)
    elif obv_trend == "down":
        score -= Decimal(3)

    if rs is not None and rs > 70:
        score += Decimal(10)

    return max(Decimal(0), min(Decimal(100), score))


def _safe_last(series) -> float | None:
    if series is None:
        return None
    try:
        val = series.iloc[-1]
        if pd.isna(val):
            return None
        return float(val)
    except (IndexError, AttributeError):
        return None


def _safe_dec(series) -> Decimal | None:
    val = _safe_last(series)
    return _dec(val) if val is not None else None


def _dec(val) -> Decimal:
    if val is None:
        return Decimal(0)
    return Decimal(str(round(float(val), 4)))
