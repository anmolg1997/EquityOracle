"""Data Quality Gate — validates data before it enters the system.

Pure domain logic: detects stale data, stock splits, outliers,
and cross-source divergence. Every check is a pure function
operating on domain objects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.core.types import DataQualityFlag, Ticker
from app.domain.market_data.models import OHLCV


@dataclass
class QualityCheckResult:
    ticker: Ticker
    flag: DataQualityFlag
    message: str
    severity: str = "info"  # "info", "warning", "critical"
    raw_value: Decimal | None = None


@dataclass
class QualityReport:
    """Aggregated quality report for a batch of data."""

    total_records: int = 0
    passed: int = 0
    flagged: int = 0
    quarantined: int = 0
    checks: list[QualityCheckResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return self.passed / self.total_records


def check_freshness(
    latest_record: OHLCV | None,
    reference_date: date,
    max_stale_days: int = 3,
) -> QualityCheckResult | None:
    """Flag data as stale if the latest record is too old.

    Accounts for weekends: a Friday record checked on Monday is NOT stale.
    """
    if latest_record is None:
        return QualityCheckResult(
            ticker=latest_record.ticker if latest_record else Ticker("UNKNOWN", "NSE", "india"),  # type: ignore[arg-type]
            flag=DataQualityFlag.STALE,
            message="No data available",
            severity="critical",
        )

    days_gap = (reference_date - latest_record.date).days

    business_days = 0
    d = latest_record.date
    while d < reference_date:
        d += timedelta(days=1)
        if d.weekday() < 5:
            business_days += 1

    if business_days > max_stale_days:
        return QualityCheckResult(
            ticker=latest_record.ticker,
            flag=DataQualityFlag.STALE,
            message=f"Data is {business_days} business days old (last: {latest_record.date})",
            severity="warning",
            raw_value=Decimal(business_days),
        )
    return None


def check_split_or_corporate_action(
    today: OHLCV,
    yesterday: OHLCV,
    threshold_pct: Decimal = Decimal("20"),
    volume_change_threshold: Decimal = Decimal("3"),
) -> QualityCheckResult | None:
    """Detect potential stock splits by checking for large price changes
    that are NOT accompanied by extreme volume changes.

    A real crash has both price drop AND volume spike.
    A split has price drop but volume stays roughly normal (or doubles).
    """
    if yesterday.close == 0:
        return None

    price_change_pct = abs((today.close - yesterday.close) / yesterday.close * 100)

    if price_change_pct < threshold_pct:
        return None

    volume_ratio = Decimal(today.volume) / Decimal(max(yesterday.volume, 1))

    if volume_ratio < volume_change_threshold:
        return QualityCheckResult(
            ticker=today.ticker,
            flag=DataQualityFlag.SPLIT_SUSPECTED,
            message=(
                f"Price changed {price_change_pct:.1f}% but volume ratio is {volume_ratio:.1f}x "
                f"— possible split/corporate action"
            ),
            severity="warning",
            raw_value=price_change_pct,
        )
    return None


def check_outlier(
    record: OHLCV,
    historical_returns: list[Decimal],
    z_threshold: float = 4.0,
) -> QualityCheckResult | None:
    """Flag daily returns that are statistical outliers (>4 sigma)."""
    if not historical_returns or len(historical_returns) < 20:
        return None

    if record.open == 0:
        return None

    current_return = float((record.close - record.open) / record.open)
    returns = [float(r) for r in historical_returns]

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance) if variance > 0 else 0.0001

    z_score = abs((current_return - mean) / std)

    if z_score > z_threshold:
        return QualityCheckResult(
            ticker=record.ticker,
            flag=DataQualityFlag.OUTLIER,
            message=f"Daily return z-score {z_score:.1f} exceeds threshold {z_threshold}",
            severity="warning",
            raw_value=Decimal(str(round(z_score, 2))),
        )
    return None


def check_cross_source_divergence(
    primary: OHLCV,
    secondary: OHLCV,
    max_divergence_pct: Decimal = Decimal("0.5"),
) -> QualityCheckResult | None:
    """Compare prices from two sources, alert if they diverge beyond threshold."""
    if primary.close == 0:
        return None

    divergence = abs((primary.close - secondary.close) / primary.close * 100)

    if divergence > max_divergence_pct:
        return QualityCheckResult(
            ticker=primary.ticker,
            flag=DataQualityFlag.DIVERGENT,
            message=(
                f"Cross-source price divergence: {divergence:.2f}% "
                f"(primary={primary.close}, secondary={secondary.close})"
            ),
            severity="warning",
            raw_value=divergence,
        )
    return None


def check_delisted(
    records: list[OHLCV],
    zero_volume_days: int = 10,
) -> QualityCheckResult | None:
    """Detect potentially delisted stocks by checking for consecutive zero-volume days."""
    if len(records) < zero_volume_days:
        return None

    recent = sorted(records, key=lambda r: r.date, reverse=True)[:zero_volume_days]
    if all(r.volume == 0 for r in recent):
        return QualityCheckResult(
            ticker=records[0].ticker,
            flag=DataQualityFlag.DELISTED,
            message=f"Zero volume for {zero_volume_days} consecutive trading days",
            severity="critical",
        )
    return None


def run_quality_gate(
    new_records: list[OHLCV],
    historical: dict[str, list[OHLCV]] | None = None,
) -> QualityReport:
    """Run all quality checks on a batch of incoming OHLCV records."""
    report = QualityReport(total_records=len(new_records))
    historical = historical or {}

    records_by_ticker: dict[str, list[OHLCV]] = {}
    for rec in new_records:
        key = str(rec.ticker)
        records_by_ticker.setdefault(key, []).append(rec)

    for key, recs in records_by_ticker.items():
        sorted_recs = sorted(recs, key=lambda r: r.date)

        for i, rec in enumerate(sorted_recs):
            flagged = False

            if i > 0:
                split_check = check_split_or_corporate_action(rec, sorted_recs[i - 1])
                if split_check:
                    report.checks.append(split_check)
                    flagged = True

            hist = historical.get(key, [])
            if hist:
                hist_returns = []
                sorted_hist = sorted(hist, key=lambda r: r.date)
                for j in range(1, len(sorted_hist)):
                    if sorted_hist[j - 1].close != 0:
                        ret = (sorted_hist[j].close - sorted_hist[j - 1].close) / sorted_hist[j - 1].close
                        hist_returns.append(ret)

                outlier_check = check_outlier(rec, hist_returns)
                if outlier_check:
                    report.checks.append(outlier_check)
                    flagged = True

        delist_check = check_delisted(sorted_recs)
        if delist_check:
            report.checks.append(delist_check)

        if not flagged:
            report.passed += len(sorted_recs)
        else:
            report.flagged += len(sorted_recs)

    return report
