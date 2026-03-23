"""Scanner service — orchestrates scanning, filtering, and scoring."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.application.scanner.filter_spec import FilterSpec
from app.application.scanner.presets import list_presets, load_preset
from app.config import settings
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
_SCAN_CACHE_SCHEMA = "v5"


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
        cache_key = f"{_SCAN_CACHE_SCHEMA}:{market.value}:{preset_name or '__all__'}:{limit}"

        with trace_span("scanner.run_scan", correlation_id=correlation_id):
            # Try serving from cache first
            if self._cache:
                cached = await self._cache.get_json("scan", cache_key)
                if cached:
                    log.info("scan_served_from_cache", market=market.value, preset=preset_name, limit=limit)
                    results_from_cache = self._deserialize_results(cached)
                    for item in results_from_cache:
                        setattr(item, "scan_source", "cache")
                    return results_from_cache

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

            scan_data: list[tuple[Ticker, TechnicalScore, Any, dict[str, Any], list[float], list[Any]]] = []

            for ticker in tickers[:500]:  # cap to avoid timeouts
                try:
                    pipeline_steps: dict[str, Any] = {
                        "universe_selected": True,
                        "ohlcv_source": "none",
                        "fundamentals_source": "none",
                        "technical_computed": False,
                        "factor_computed": False,
                        "composite_computed": False,
                        "preset_evaluated": bool(preset_name),
                        "preset_passed": False,
                    }
                    ohlcv = await self._repo.get_ohlcv(ticker, start, end)
                    if not ohlcv or len(ohlcv) < 50:
                        ohlcv = await self._provider.get_ohlcv(ticker, start, end)
                        pipeline_steps["ohlcv_source"] = "provider"
                        if ohlcv:
                            try:
                                await self._repo.save_ohlcv_batch(ohlcv)
                            except Exception as save_err:
                                log.debug("scan_ohlcv_persist_error", ticker=str(ticker), error=str(save_err))
                    else:
                        pipeline_steps["ohlcv_source"] = "repository"

                    if not ohlcv or len(ohlcv) < 20:
                        continue

                    sparkline = self._build_sparkline(ohlcv)
                    tech_score = compute_technical_score(ticker, ohlcv)
                    pipeline_steps["technical_computed"] = True
                    fundamentals = await self._repo.get_fundamentals(ticker)
                    if not fundamentals:
                        fundamentals = await self._provider.get_fundamentals(ticker)
                        pipeline_steps["fundamentals_source"] = "provider" if fundamentals else "none"
                        if fundamentals:
                            try:
                                await self._repo.save_fundamentals(fundamentals)
                            except Exception as save_err:
                                log.debug("scan_fundamentals_persist_error", ticker=str(ticker), error=str(save_err))
                    else:
                        pipeline_steps["fundamentals_source"] = "repository"

                    factor_score = compute_factor_scores(ticker, ohlcv, fundamentals)
                    pipeline_steps["factor_computed"] = True

                    key = str(ticker)
                    all_tech_scores[key] = float(tech_score.score)
                    all_fund_scores[key] = float(factor_score.quality_score)
                    all_value_scores[key] = float(factor_score.value_score)
                    all_mom_scores[key] = float(factor_score.momentum_score)

                    scan_data.append((ticker, tech_score, factor_score, pipeline_steps, sparkline, ohlcv))

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

                for ticker, tech, factor, pipeline_steps, sparkline, ohlcv in scan_data:
                    composite = compute_composite(
                        ticker=ticker,
                        technical=tech,
                        factor=factor,
                        effective_signal_count=decorr.effective_signal_count,
                        pillar_correlations=decorr.pairwise_correlations,
                        adaptive_missing_pillars=settings.scanner_adaptive_weighting,
                        sentiment_available=False,
                        ml_available=False,
                    )
                    pipeline_steps["composite_computed"] = True
                    adaptive_preview = compute_composite(
                        ticker=ticker,
                        technical=tech,
                        factor=factor,
                        effective_signal_count=decorr.effective_signal_count,
                        pillar_correlations=decorr.pairwise_correlations,
                        adaptive_missing_pillars=True,
                        sentiment_available=False,
                        ml_available=False,
                    )

                    passed = []
                    if preset_name:
                        try:
                            spec = load_preset(preset_name)
                            data_dict = self._to_filter_dict(tech, factor)
                            if spec.evaluate(data_dict):
                                passed.append(preset_name)
                                pipeline_steps["preset_passed"] = True
                        except FileNotFoundError:
                            pass

                    scan_result = ScanResult(
                        ticker=ticker,
                        composite_score=composite,
                        technical_score=tech,
                        factor_score=factor,
                        passed_presets=passed,
                    )
                    setattr(scan_result, "pipeline_steps", pipeline_steps)
                    setattr(scan_result, "sparkline", sparkline)
                    setattr(
                        scan_result,
                        "contribution_breakdown",
                        self._build_contributions(
                            composite=composite,
                            technical=tech.score,
                            fundamental=factor.composite,
                            sentiment_input=Decimal(50),
                            ml_input=Decimal(0),
                            adaptive_preview=adaptive_preview.overall,
                        ),
                    )
                    setattr(
                        scan_result,
                        "forecast",
                        self._build_forecast(
                            ohlcv=ohlcv,
                            horizon_days=5,
                        ),
                    )
                    setattr(scan_result, "scan_source", "fresh")
                    results.append(scan_result)

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
                "pipeline_steps": getattr(r, "pipeline_steps", {}),
                "sparkline": getattr(r, "sparkline", []),
                "contribution_breakdown": getattr(r, "contribution_breakdown", {}),
                "forecast": getattr(r, "forecast", {}),
                "scan_source": getattr(r, "scan_source", "fresh"),
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
            setattr(results[-1], "pipeline_steps", row.get("pipeline_steps", {}))
            setattr(results[-1], "sparkline", row.get("sparkline", []))
            setattr(results[-1], "contribution_breakdown", row.get("contribution_breakdown", {}))
            setattr(results[-1], "forecast", row.get("forecast", {}))
            setattr(results[-1], "scan_source", row.get("scan_source", "cache"))

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

    def _build_sparkline(self, ohlcv: list[Any], points: int = 24) -> list[float]:
        return [float(c.close) for c in ohlcv[-points:]]

    def _build_contributions(
        self,
        composite: CompositeScore,
        technical: Decimal,
        fundamental: Decimal,
        sentiment_input: Decimal,
        ml_input: Decimal,
        adaptive_preview: Decimal,
    ) -> dict[str, Any]:
        w = composite.weights_used
        tech_w = w.get("technical", 0.0)
        fund_w = w.get("fundamental", 0.0)
        sent_w = w.get("sentiment", 0.0)
        ml_w = w.get("ml_prediction", 0.0)
        return {
            "inputs": {
                "technical": float(technical),
                "fundamental": float(fundamental),
                "sentiment": float(sentiment_input),
                "ml_prediction": float(ml_input),
            },
            "weights": {
                "technical": tech_w,
                "fundamental": fund_w,
                "sentiment": sent_w,
                "ml_prediction": ml_w,
            },
            "weighted_contributions": {
                "technical": round(float(technical) * tech_w, 2),
                "fundamental": round(float(fundamental) * fund_w, 2),
                "sentiment": round(float(sentiment_input) * sent_w, 2),
                "ml_prediction": round(float(ml_input) * ml_w, 2),
            },
            "overall": float(composite.overall),
            "overall_adaptive_preview": float(adaptive_preview),
            "adaptive_weighting_enabled": settings.scanner_adaptive_weighting,
            "explainers": [
                "Overall is a weighted sum across all pillars, not a simple average of visible pillars.",
                "Scanner uses neutral sentiment input and ML input zero unless those models are explicitly enabled.",
            ],
        }

    def _build_forecast(self, ohlcv: list[Any], horizon_days: int = 5) -> dict[str, Any]:
        closes = [float(getattr(c, "close", 0.0)) for c in ohlcv if getattr(c, "close", None) is not None]
        if len(closes) < max(60, horizon_days + 5):
            return {}

        daily_returns = [
            (closes[i] / closes[i - 1]) - 1.0
            for i in range(1, len(closes))
            if closes[i - 1] > 0
        ]
        if len(daily_returns) < 40:
            return {}

        horizon_returns = [
            (closes[i + horizon_days] / closes[i]) - 1.0
            for i in range(0, len(closes) - horizon_days)
            if closes[i] > 0
        ]
        if len(horizon_returns) < 30:
            return {}

        sample_size = len(horizon_returns)
        mean_ret = sum(horizon_returns) / sample_size
        variance = sum((r - mean_ret) ** 2 for r in horizon_returns) / max(sample_size - 1, 1)
        std_ret = variance ** 0.5
        std_ret = max(std_ret, 1e-6)

        # Regime transition probability from daily-return sign Markov transitions.
        pp = pn = np = nn = 1.0  # Laplace smoothing
        for i in range(1, len(daily_returns)):
            prev_up = daily_returns[i - 1] >= 0
            cur_up = daily_returns[i] >= 0
            if prev_up and cur_up:
                pp += 1.0
            elif prev_up and not cur_up:
                pn += 1.0
            elif (not prev_up) and cur_up:
                np += 1.0
            else:
                nn += 1.0

        current_up = daily_returns[-1] >= 0
        if current_up:
            p_up_next = pp / (pp + pn)
        else:
            p_up_next = np / (np + nn)
        p_down_next = 1.0 - p_up_next

        # Regime-aware mean shift; modest to avoid overfitting a single transition.
        mean_adj = mean_ret + (p_up_next - 0.5) * std_ret * 0.4

        def _quantile(values: list[float], q: float) -> float:
            arr = sorted(values)
            idx = int(round((len(arr) - 1) * q))
            idx = max(0, min(idx, len(arr) - 1))
            return arr[idx]

        q20 = _quantile(horizon_returns, 0.2)
        q50 = _quantile(horizon_returns, 0.5)
        q80 = _quantile(horizon_returns, 0.8)

        lower_bear = mean_adj - 0.9 * std_ret
        upper_base = mean_adj + 0.3 * std_ret
        upper_bull = mean_adj + 1.15 * std_ret

        buckets: dict[str, list[float]] = {
            "bear": [],
            "base": [],
            "bull": [],
            "stretch": [],
        }
        for r in horizon_returns:
            if r <= lower_bear:
                buckets["bear"].append(r)
            elif r <= upper_base:
                buckets["base"].append(r)
            elif r <= upper_bull:
                buckets["bull"].append(r)
            else:
                buckets["stretch"].append(r)

        alpha = 1.5
        denom = sample_size + alpha * 4
        probs = {
            k: (len(v) + alpha) / denom
            for k, v in buckets.items()
        }

        def _scenario_mean(values: list[float], fallback: float) -> float:
            if values:
                return sum(values) / len(values)
            return fallback

        scenarios = [
            {
                "id": "bear",
                "label": "Bear path",
                "probability": round(probs["bear"], 4),
                "expected_return": round(_scenario_mean(buckets["bear"], mean_adj - 1.0 * std_ret), 4),
                "mean_reversion_risk": True,
            },
            {
                "id": "base",
                "label": "Base path",
                "probability": round(probs["base"], 4),
                "expected_return": round(_scenario_mean(buckets["base"], mean_adj), 4),
                "mean_reversion_risk": False,
            },
            {
                "id": "bull",
                "label": "Bull path",
                "probability": round(probs["bull"], 4),
                "expected_return": round(_scenario_mean(buckets["bull"], mean_adj + 0.7 * std_ret), 4),
                "mean_reversion_risk": False,
            },
            {
                "id": "stretch",
                "label": "Stretch path",
                "probability": round(probs["stretch"], 4),
                "expected_return": round(_scenario_mean(buckets["stretch"], mean_adj + 1.4 * std_ret), 4),
                "mean_reversion_risk": False,
            },
        ]

        # Normalize probabilities to exactly 1.0 after rounding.
        total_prob = sum(s["probability"] for s in scenarios)
        if total_prob > 0:
            for s in scenarios:
                s["probability"] = round(s["probability"] / total_prob, 4)
            drift = 1.0 - sum(s["probability"] for s in scenarios)
            scenarios[1]["probability"] = round(scenarios[1]["probability"] + drift, 4)

        return {
            "model": "empirical_markov_horizon",
            "horizon_days": horizon_days,
            "sample_size": sample_size,
            "distribution": {
                "mean_return": round(mean_adj, 4),
                "std_return": round(std_ret, 4),
                "q20": round(q20, 4),
                "q50": round(q50, 4),
                "q80": round(q80, 4),
            },
            "regime": {
                "current": "up" if current_up else "down",
                "p_up_next": round(p_up_next, 4),
                "p_down_next": round(p_down_next, 4),
            },
            "scenarios": scenarios,
        }
