"""50+ technical features via pandas-ta."""

from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from app.domain.market_data.models import OHLCV


def compute_technical_features(ohlcv: list[OHLCV]) -> pd.DataFrame:
    """Compute a comprehensive set of technical features from OHLCV data."""
    if not ohlcv:
        return pd.DataFrame()

    df = _to_dataframe(ohlcv)

    features = pd.DataFrame(index=df.index)

    # Price momentum features
    for period in [5, 10, 20, 60, 120, 252]:
        if len(df) > period:
            features[f"return_{period}d"] = df["close"].pct_change(period)

    # Moving averages
    for period in [5, 10, 20, 50, 100, 200]:
        if len(df) > period:
            sma = df["close"].rolling(period).mean()
            features[f"sma_{period}_ratio"] = df["close"] / sma
            features[f"sma_{period}_slope"] = sma.pct_change(5)

    # RSI at multiple timeframes
    for period in [7, 14, 21]:
        rsi = df.ta.rsi(length=period)
        if rsi is not None:
            features[f"rsi_{period}"] = rsi

    # MACD
    macd = df.ta.macd(fast=12, slow=26, signal=9)
    if macd is not None:
        features["macd_line"] = macd.iloc[:, 0]
        features["macd_signal"] = macd.iloc[:, 1]
        features["macd_histogram"] = macd.iloc[:, 2]

    # Bollinger Bands
    bb = df.ta.bbands(length=20)
    if bb is not None and len(bb.columns) >= 3:
        bb_lower = bb.iloc[:, 0]
        bb_mid = bb.iloc[:, 1]
        bb_upper = bb.iloc[:, 2]
        bb_width = bb_upper - bb_lower
        features["bb_position"] = (df["close"] - bb_lower) / bb_width.replace(0, float("nan"))
        features["bb_width"] = bb_width / bb_mid.replace(0, float("nan"))

    # ADX
    adx = df.ta.adx(length=14)
    if adx is not None:
        features["adx_14"] = adx.iloc[:, 0]
        features["di_plus"] = adx.iloc[:, 1] if len(adx.columns) > 1 else None
        features["di_minus"] = adx.iloc[:, 2] if len(adx.columns) > 2 else None

    # ATR
    atr = df.ta.atr(length=14)
    if atr is not None:
        features["atr_14"] = atr
        features["atr_pct"] = atr / df["close"]

    # Volume features
    features["volume_ratio_20d"] = df["volume"] / df["volume"].rolling(20).mean()
    features["volume_ratio_50d"] = df["volume"] / df["volume"].rolling(50).mean()

    obv = df.ta.obv()
    if obv is not None:
        features["obv"] = obv
        features["obv_slope_20d"] = obv.pct_change(20)

    # Stochastic
    stoch = df.ta.stoch(k=14, d=3)
    if stoch is not None:
        features["stoch_k"] = stoch.iloc[:, 0]
        features["stoch_d"] = stoch.iloc[:, 1]

    # Williams %R
    willr = df.ta.willr(length=14)
    if willr is not None:
        features["williams_r"] = willr

    # CCI
    cci = df.ta.cci(length=20)
    if cci is not None:
        features["cci_20"] = cci

    # MFI
    mfi = df.ta.mfi(length=14)
    if mfi is not None:
        features["mfi_14"] = mfi

    # Price pattern features
    features["higher_high"] = (df["high"] > df["high"].shift(1)).astype(int)
    features["lower_low"] = (df["low"] < df["low"].shift(1)).astype(int)
    features["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"]).replace(0, float("nan"))

    # Volatility features
    features["volatility_20d"] = df["close"].pct_change().rolling(20).std()
    features["volatility_60d"] = df["close"].pct_change().rolling(60).std()
    features["vol_ratio"] = features.get("volatility_20d", 0) / features.get("volatility_60d", float("nan"))

    # Gap features
    features["gap_pct"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)

    # Distance from 52-week high/low
    if len(df) >= 252:
        features["dist_from_52w_high"] = (df["close"] - df["high"].rolling(252).max()) / df["high"].rolling(252).max()
        features["dist_from_52w_low"] = (df["close"] - df["low"].rolling(252).min()) / df["low"].rolling(252).min()

    return features


def _to_dataframe(ohlcv: list[OHLCV]) -> pd.DataFrame:
    data = {
        "open": [float(r.open) for r in ohlcv],
        "high": [float(r.high) for r in ohlcv],
        "low": [float(r.low) for r in ohlcv],
        "close": [float(r.close) for r in ohlcv],
        "volume": [float(r.volume) for r in ohlcv],
    }
    df = pd.DataFrame(data, index=[r.date for r in ohlcv])
    df.sort_index(inplace=True)
    return df
