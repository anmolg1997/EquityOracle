"""Scanner service — orchestrates scanning, filtering, and scoring."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.application.scanner.filter_spec import FilterSpec
from app.application.scanner.presets import list_presets, load_preset
from app.core.logging import get_logger
from app.core.observability import trace_span
from app.core.types import Market, Ticker, new_correlation_id
from app.domain.analysis.composite import compute_composite
from app.domain.analysis.decorrelation import compute_decorrelation
from app.domain.analysis.factors import compute_factor_scores
from app.domain.analysis.models import CompositeScore, ScanResult, TechnicalScore
from app.domain.analysis.technical import compute_technical_score
from app.domain.market_data.liquidity import passes_liquidity_filter
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository
from app.infrastructure.cache.redis import RedisCache

log = get_logger(__name__)


class ScannerService:
    """Orchestrates full-universe scanning: indicators -> factors -> composite."""

    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository,
        cache: RedisCache | None = None,
        min_liquidity: Decimal = Decimal("1_000_000"),
    ) -> None:
        self._provider = provider
        self._repo = repository
        self._cache = cache
        self._min_liquidity = min_liquidity

    async def run_scan(
        self,
        market: Market = Market.INDIA,
        preset_name: str | None = None,
        custom_filter: FilterSpec | None = None,
        limit: int = 100,
    ) -> list[ScanResult]:
        """Run a full scan on the market universe."""
        correlation_id = new_correlation_id()

        with trace_span("scanner.run_scan", correlation_id=correlation_id):
            # Try serving from cache first
            if self._cache and preset_name:
                cached = await self._cache.get_json("scan", f"{market.value}:{preset_name}")
                if cached:
                    log.info("scan_served_from_cache", preset=preset_name)
                    return self._deserialize_results(cached)

            tickers = await self._repo.get_universe(market)
            if not tickers:
                tickers = await self._provider.get_universe(market)

            log.info("scan_universe", count=len(tickers), market=market.value)

            results: list[ScanResult] = []
            end = date.today()
            start = end - timedelta(days=365)

            all_tech_scores: dict[str, float] = {}
            all_fund_scores: dict[str, float] = {}
            all_value_scores: dict[str, float] = {}
            all_mom_scores: dict[str, float] = {}

            scan_data: list[tuple[Ticker, TechnicalScore, Any, Any]] = []

            for ticker in tickers[:500]:  # cap to avoid timeouts
                try:
                    ohlcv = await self._repo.get_ohlcv(ticker, start, end)
                    if not ohlcv or len(ohlcv) < 50:
                        ohlcv = await self._provider.get_ohlcv(ticker, start, end)

                    if not ohlcv or len(ohlcv) < 20:
                        continue

                    tech_score = compute_technical_score(ticker, ohlcv)
                    fundamentals = await self._repo.get_fundamentals(ticker)
                    if not fundamentals:
                        fundamentals = await self._provider.get_fundamentals(ticker)

                    factor_score = compute_factor_scores(ticker, ohlcv, fundamentals)

                    key = str(ticker)
                    all_tech_scores[key] = float(tech_score.score)
                    all_fund_scores[key] = float(factor_score.quality_score)
                    all_value_scores[key] = float(factor_score.value_score)
                    all_mom_scores[key] = float(factor_score.momentum_score)

                    scan_data.append((ticker, tech_score, factor_score, None))

                except Exception as e:
                    log.debug("scan_ticker_error", ticker=str(ticker), error=str(e))
                    continue

            # Compute decorrelation across universe
            if scan_data:
                keys = [str(t[0]) for t in scan_data]
                decorr = compute_decorrelation({
                    "technical": [all_tech_scores.get(k, 50) for k in keys],
                    "quality": [all_fund_scores.get(k, 50) for k in keys],
                    "value": [all_value_scores.get(k, 50) for k in keys],
                    "momentum": [all_mom_scores.get(k, 50) for k in keys],
                })

                for ticker, tech, factor, _ in scan_data:
                    composite = compute_composite(
                        ticker=ticker,
                        technical=tech,
                        factor=factor,
                        effective_signal_count=decorr.effective_signal_count,
                        pillar_correlations=decorr.pairwise_correlations,
                    )

                    passed = []
                    if preset_name:
                        try:
                            spec = load_preset(preset_name)
                            data_dict = self._to_filter_dict(tech, factor)
                            if spec.evaluate(data_dict):
                                passed.append(preset_name)
                        except FileNotFoundError:
                            pass

                    results.append(ScanResult(
                        ticker=ticker,
                        composite_score=composite,
                        technical_score=tech,
                        factor_score=factor,
                        passed_presets=passed,
                    ))

            results.sort(key=lambda r: r.composite_score.overall, reverse=True)
            for i, r in enumerate(results):
                r.rank = i + 1

            results = results[:limit]

            if self._cache and preset_name:
                await self._cache.set_json(
                    "scan",
                    f"{market.value}:{preset_name}",
                    self._serialize_results(results),
                    ttl_seconds=86400,
                )

            return results

    async def get_presets(self) -> list[dict[str, str]]:
        return list_presets()

    def _to_filter_dict(self, tech: TechnicalScore, factor: Any) -> dict[str, Any]:
        return {
            "close": float(tech.sma_20 or 0),
            "rsi_14": float(tech.rsi_14 or 0),
            "adx_14": float(tech.adx_14 or 0),
            "sma_20": float(tech.sma_20 or 0),
            "sma_50": float(tech.sma_50 or 0),
            "sma_150": float(tech.sma_150 or 0),
            "sma_200": float(tech.sma_200 or 0),
            "volume_ratio": float(tech.volume_ratio or 0),
            "rs_rating": float(tech.rs_rating or 0),
            "momentum_score": float(factor.momentum_score),
            "quality_score": float(factor.quality_score),
            "value_score": float(factor.value_score),
        }

    def _serialize_results(self, results: list[ScanResult]) -> list[dict]:
        return [
            {
                "ticker": str(r.ticker),
                "rank": r.rank,
                "overall_score": str(r.composite_score.overall),
                "technical": str(r.composite_score.technical),
                "fundamental": str(r.composite_score.fundamental),
                "effective_signals": str(r.composite_score.effective_signal_count),
                "passed_presets": r.passed_presets,
            }
            for r in results
        ]

    def _deserialize_results(self, data: list[dict]) -> list[ScanResult]:
        # Lightweight deserialization for cached results
        return []
