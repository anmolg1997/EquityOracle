"""Scanner service — orchestrates scanning, filtering, and scoring."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.application.scanner.filter_spec import FilterSpec
from app.application.scanner.presets import list_presets, load_preset
from app.core.logging import get_logger
from app.core.observability import trace_span
from app.core.types import Exchange, Market, Ticker, new_correlation_id
from app.domain.analysis.composite import compute_composite
from app.domain.analysis.decorrelation import compute_decorrelation
from app.domain.analysis.factors import compute_factor_scores
from app.domain.analysis.models import CompositeScore, FactorScore, ScanResult, TechnicalScore
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
        cache_key = f"{market.value}:{preset_name or '__all__'}:{limit}"

        with trace_span("scanner.run_scan", correlation_id=correlation_id):
            # Try serving from cache first
            if self._cache:
                cached = await self._cache.get_json("scan", cache_key)
                if cached:
                    log.info("scan_served_from_cache", market=market.value, preset=preset_name, limit=limit)
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
                        if ohlcv:
                            try:
                                await self._repo.save_ohlcv_batch(ohlcv)
                            except Exception as save_err:
                                log.debug("scan_ohlcv_persist_error", ticker=str(ticker), error=str(save_err))

                    if not ohlcv or len(ohlcv) < 20:
                        continue

                    tech_score = compute_technical_score(ticker, ohlcv)
                    fundamentals = await self._repo.get_fundamentals(ticker)
                    if not fundamentals:
                        fundamentals = await self._provider.get_fundamentals(ticker)
                        if fundamentals:
                            try:
                                await self._repo.save_fundamentals(fundamentals)
                            except Exception as save_err:
                                log.debug("scan_fundamentals_persist_error", ticker=str(ticker), error=str(save_err))

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

            if self._cache:
                await self._cache.set_json(
                    "scan",
                    cache_key,
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
                "symbol": r.ticker.symbol,
                "exchange": r.ticker.exchange.value,
                "market": r.ticker.market.value,
                "rank": r.rank,
                "overall_score": float(r.composite_score.overall),
                "technical": float(r.composite_score.technical),
                "fundamental": float(r.composite_score.fundamental),
                "effective_signals": float(r.composite_score.effective_signal_count),
                "confidence": r.composite_score.confidence_level,
                "technical_indicators": {
                    "score": float(r.technical_score.score),
                    "rsi_14": self._dec_to_float(r.technical_score.rsi_14),
                    "macd_histogram": self._dec_to_float(r.technical_score.macd_histogram),
                    "adx_14": self._dec_to_float(r.technical_score.adx_14),
                    "volume_ratio": self._dec_to_float(r.technical_score.volume_ratio),
                    "rs_rating": self._dec_to_float(r.technical_score.rs_rating),
                    "obv_trend": r.technical_score.obv_trend,
                },
                "factor_components": {
                    "composite": float(r.factor_score.composite),
                    "momentum_score": float(r.factor_score.momentum_score),
                    "quality_score": float(r.factor_score.quality_score),
                    "value_score": float(r.factor_score.value_score),
                    "momentum_details": r.factor_score.momentum_details,
                    "quality_details": r.factor_score.quality_details,
                    "value_details": r.factor_score.value_details,
                },
                "passed_presets": r.passed_presets,
            }
            for r in results
        ]

    def _deserialize_results(self, data: list[dict]) -> list[ScanResult]:
        results: list[ScanResult] = []
        today = date.today()

        for row in data:
            ticker = self._ticker_from_cache_row(row)
            if ticker is None:
                continue

            technical = Decimal(str(row.get("technical", 0)))
            fundamental = Decimal(str(row.get("fundamental", 0)))
            overall = Decimal(str(row.get("overall_score", 0)))
            effective_signals = Decimal(str(row.get("effective_signals", 0)))
            tech_details = row.get("technical_indicators") or {}
            factor_details = row.get("factor_components") or {}

            composite = CompositeScore(
                ticker=ticker,
                as_of_date=today,
                technical=technical,
                fundamental=fundamental,
                overall=overall,
                effective_signal_count=effective_signals,
            )

            tech_score = TechnicalScore(
                ticker=ticker,
                as_of_date=today,
                score=technical,
                rsi_14=self._float_to_dec(tech_details.get("rsi_14")),
                macd_histogram=self._float_to_dec(tech_details.get("macd_histogram")),
                adx_14=self._float_to_dec(tech_details.get("adx_14")),
                volume_ratio=self._float_to_dec(tech_details.get("volume_ratio")),
                rs_rating=self._float_to_dec(tech_details.get("rs_rating")),
                obv_trend=str(tech_details.get("obv_trend", "")),
            )
            factor_score = FactorScore(
                ticker=ticker,
                as_of_date=today,
                composite=self._float_to_dec(factor_details.get("composite")) or fundamental,
                momentum_score=self._float_to_dec(factor_details.get("momentum_score")) or Decimal(0),
                quality_score=self._float_to_dec(factor_details.get("quality_score")) or fundamental,
                value_score=self._float_to_dec(factor_details.get("value_score")) or Decimal(0),
                momentum_details=factor_details.get("momentum_details") or {},
                quality_details=factor_details.get("quality_details") or {},
                value_details=factor_details.get("value_details") or {},
            )

            results.append(
                ScanResult(
                    ticker=ticker,
                    composite_score=composite,
                    technical_score=tech_score,
                    factor_score=factor_score,
                    passed_presets=row.get("passed_presets", []),
                    rank=int(row.get("rank", 0)),
                )
            )

        results.sort(key=lambda r: r.rank if r.rank > 0 else 10_000)
        return results

    def _ticker_from_cache_row(self, row: dict[str, Any]) -> Ticker | None:
        symbol = row.get("symbol")
        exchange = row.get("exchange")
        market = row.get("market")

        if symbol and exchange and market:
            try:
                return Ticker(
                    symbol=str(symbol),
                    exchange=Exchange(str(exchange)),
                    market=Market(str(market)),
                )
            except Exception:
                pass

        ticker_raw = str(row.get("ticker", ""))
        if ":" not in ticker_raw:
            return None

        sym, ex = ticker_raw.split(":", 1)
        try:
            return Ticker(
                symbol=sym,
                exchange=Exchange(ex),
                market=Market(str(market)) if market else Market.INDIA,
            )
        except Exception:
            return None

    def _dec_to_float(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _float_to_dec(self, value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
