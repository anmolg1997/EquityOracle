"""Market Data domain services — validation, normalization, split adjustment."""

from __future__ import annotations

from decimal import Decimal

from app.domain.market_data.models import OHLCV


def adjust_for_split(
    records: list[OHLCV],
    split_ratio: Decimal,
    split_date_index: int,
) -> list[OHLCV]:
    """Adjust historical prices before a split date by the split ratio.

    split_ratio = new_shares / old_shares (e.g., 2.0 for a 2:1 split).
    Records before split_date_index are adjusted.
    """
    adjusted: list[OHLCV] = []
    for i, rec in enumerate(records):
        if i < split_date_index:
            adjusted.append(
                OHLCV(
                    ticker=rec.ticker,
                    date=rec.date,
                    open=rec.open / split_ratio,
                    high=rec.high / split_ratio,
                    low=rec.low / split_ratio,
                    close=rec.close / split_ratio,
                    volume=int(rec.volume * int(split_ratio)),
                    adjusted_close=rec.adjusted_close / split_ratio if rec.adjusted_close else None,
                    data_quality=rec.data_quality,
                    available_at=rec.available_at,
                )
            )
        else:
            adjusted.append(rec)
    return adjusted


def compute_daily_returns(records: list[OHLCV]) -> list[Decimal]:
    """Compute close-to-close daily returns from sorted OHLCV records."""
    sorted_recs = sorted(records, key=lambda r: r.date)
    returns: list[Decimal] = []
    for i in range(1, len(sorted_recs)):
        prev_close = sorted_recs[i - 1].close
        if prev_close == 0:
            continue
        ret = (sorted_recs[i].close - prev_close) / prev_close
        returns.append(ret)
    return returns


def validate_ohlcv(record: OHLCV) -> list[str]:
    """Validate basic OHLCV invariants, return list of violation messages."""
    violations: list[str] = []
    if record.high < record.low:
        violations.append(f"High ({record.high}) < Low ({record.low})")
    if record.close < 0 or record.open < 0:
        violations.append("Negative price detected")
    if record.volume < 0:
        violations.append("Negative volume")
    if record.high < record.close or record.high < record.open:
        violations.append("High is not the highest price")
    if record.low > record.close or record.low > record.open:
        violations.append("Low is not the lowest price")
    return violations
