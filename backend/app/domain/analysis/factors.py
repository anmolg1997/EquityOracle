"""Factor scoring — Momentum, Quality, Value computation.

Pure domain logic: takes domain models, returns factor scores.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.types import Ticker
from app.domain.analysis.models import FactorScore
from app.domain.market_data.models import FundamentalData, OHLCV


def compute_factor_scores(
    ticker: Ticker,
    ohlcv: list[OHLCV],
    fundamentals: FundamentalData | None,
    as_of: date | None = None,
) -> FactorScore:
    """Compute momentum, quality, and value factor scores."""
    as_of = as_of or date.today()

    momentum = _compute_momentum(ohlcv)
    quality = _compute_quality(fundamentals)
    value = _compute_value(fundamentals)

    composite = (momentum["score"] + quality["score"] + value["score"]) / 3

    return FactorScore(
        ticker=ticker,
        as_of_date=as_of,
        momentum_score=momentum["score"],
        quality_score=quality["score"],
        value_score=value["score"],
        composite=composite,
        momentum_details=momentum,
        quality_details=quality,
        value_details=value,
    )


def _compute_momentum(ohlcv: list[OHLCV]) -> dict:
    """Momentum: 6m and 12m returns, excluding the most recent month.

    Skipping the most recent month avoids short-term reversal effects.
    """
    if len(ohlcv) < 22:
        return {"score": Decimal(50), "reason": "insufficient_data"}

    sorted_data = sorted(ohlcv, key=lambda r: r.date)

    skip_recent = sorted_data[:-22] if len(sorted_data) > 22 else sorted_data
    current_price = skip_recent[-1].close if skip_recent else sorted_data[-1].close

    ret_6m = None
    if len(sorted_data) >= 126:
        ref = sorted_data[-126].close
        if ref > 0:
            ret_6m = float((current_price - ref) / ref * 100)

    ret_12m = None
    if len(sorted_data) >= 252:
        ref = sorted_data[-252].close
        if ref > 0:
            ret_12m = float((current_price - ref) / ref * 100)

    score = Decimal(50)
    if ret_6m is not None:
        if ret_6m > 30:
            score += Decimal(25)
        elif ret_6m > 15:
            score += Decimal(15)
        elif ret_6m > 0:
            score += Decimal(5)
        elif ret_6m < -15:
            score -= Decimal(15)
        else:
            score -= Decimal(5)

    if ret_12m is not None:
        if ret_12m > 50:
            score += Decimal(20)
        elif ret_12m > 20:
            score += Decimal(10)
        elif ret_12m < -20:
            score -= Decimal(10)

    return {
        "score": max(Decimal(0), min(Decimal(100), score)),
        "return_6m_pct": ret_6m,
        "return_12m_pct": ret_12m,
    }


def _compute_quality(fundamentals: FundamentalData | None) -> dict:
    """Quality: 3yr net profit growth + operating margin + ROE."""
    if fundamentals is None:
        return {"score": Decimal(50), "reason": "no_fundamentals"}

    score = Decimal(50)

    if fundamentals.profit_growth_3yr is not None:
        g = float(fundamentals.profit_growth_3yr * 100)
        if g > 20:
            score += Decimal(20)
        elif g > 10:
            score += Decimal(10)
        elif g < 0:
            score -= Decimal(10)

    if fundamentals.operating_profit_margin is not None:
        opm = float(fundamentals.operating_profit_margin * 100)
        if opm > 20:
            score += Decimal(15)
        elif opm > 10:
            score += Decimal(8)
        elif opm < 5:
            score -= Decimal(10)

    if fundamentals.roe is not None:
        roe_val = float(fundamentals.roe * 100)
        if roe_val > 20:
            score += Decimal(15)
        elif roe_val > 12:
            score += Decimal(8)
        elif roe_val < 5:
            score -= Decimal(10)

    return {
        "score": max(Decimal(0), min(Decimal(100), score)),
        "profit_growth_3yr": float(fundamentals.profit_growth_3yr * 100) if fundamentals.profit_growth_3yr else None,
        "opm": float(fundamentals.operating_profit_margin * 100) if fundamentals.operating_profit_margin else None,
        "roe": float(fundamentals.roe * 100) if fundamentals.roe else None,
    }


def _compute_value(fundamentals: FundamentalData | None) -> dict:
    """Value: EBITDA/EV, earnings yield, P/E, P/B."""
    if fundamentals is None:
        return {"score": Decimal(50), "reason": "no_fundamentals"}

    score = Decimal(50)

    if fundamentals.pe_ratio is not None:
        pe = float(fundamentals.pe_ratio)
        if 0 < pe < 12:
            score += Decimal(20)
        elif 12 <= pe < 20:
            score += Decimal(10)
        elif pe > 40:
            score -= Decimal(15)
        elif pe > 25:
            score -= Decimal(5)

    if fundamentals.pb_ratio is not None:
        pb = float(fundamentals.pb_ratio)
        if 0 < pb < 1.5:
            score += Decimal(15)
        elif pb < 3:
            score += Decimal(5)
        elif pb > 5:
            score -= Decimal(10)

    if fundamentals.ev_ebitda is not None:
        ev_eb = float(fundamentals.ev_ebitda)
        if 0 < ev_eb < 8:
            score += Decimal(15)
        elif ev_eb < 15:
            score += Decimal(5)
        elif ev_eb > 25:
            score -= Decimal(10)

    return {
        "score": max(Decimal(0), min(Decimal(100), score)),
        "pe": float(fundamentals.pe_ratio) if fundamentals.pe_ratio else None,
        "pb": float(fundamentals.pb_ratio) if fundamentals.pb_ratio else None,
        "ev_ebitda": float(fundamentals.ev_ebitda) if fundamentals.ev_ebitda else None,
    }
