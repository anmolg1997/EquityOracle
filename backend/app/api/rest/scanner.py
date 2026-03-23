"""Scanner REST API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_cache, get_data_provider, get_market_data_repository
from app.application.scanner.service import ScannerService
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository
from app.infrastructure.cache.redis import RedisCache
from app.core.types import Market

router = APIRouter(prefix="/scanner", tags=["scanner"])


def _as_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return None


@router.get("/scan")
async def run_scan(
    market: str = Query(default="india"),
    preset: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    repository: MarketDataRepository = Depends(get_market_data_repository),
    provider: MarketDataProvider = Depends(get_data_provider),
    cache: RedisCache = Depends(get_cache),
) -> dict:
    service = ScannerService(
        provider=provider,
        repository=repository,
        cache=cache,
    )
    results = await service.run_scan(
        market=Market(market),
        preset_name=preset,
        limit=limit,
    )
    return {
        "count": len(results),
        "market": market,
        "preset": preset,
        "results": [
            {
                "rank": r.rank,
                "ticker": str(r.ticker),
                "overall_score": float(r.composite_score.overall),
                "technical_score": float(r.composite_score.technical),
                "fundamental_score": float(r.composite_score.fundamental),
                "effective_signals": float(r.composite_score.effective_signal_count),
                "confidence": r.composite_score.confidence_level,
                "passed_presets": r.passed_presets,
                "diagnostics": {
                    "composite": {
                        "overall": float(r.composite_score.overall),
                        "technical": float(r.composite_score.technical),
                        "fundamental": float(r.composite_score.fundamental),
                        "effective_signals": float(r.composite_score.effective_signal_count),
                        "confidence": r.composite_score.confidence_level,
                    },
                    "technical": {
                        "score": float(r.technical_score.score),
                        "rsi_14": _as_float(r.technical_score.rsi_14),
                        "macd_histogram": _as_float(r.technical_score.macd_histogram),
                        "adx_14": _as_float(r.technical_score.adx_14),
                        "volume_ratio": _as_float(r.technical_score.volume_ratio),
                        "rs_rating": _as_float(r.technical_score.rs_rating),
                        "obv_trend": r.technical_score.obv_trend,
                    },
                    "factor": {
                        "composite": float(r.factor_score.composite),
                        "momentum_score": float(r.factor_score.momentum_score),
                        "quality_score": float(r.factor_score.quality_score),
                        "value_score": float(r.factor_score.value_score),
                        "momentum_details": r.factor_score.momentum_details,
                        "quality_details": r.factor_score.quality_details,
                        "value_details": r.factor_score.value_details,
                    },
                    "preset": {
                        "selected": preset,
                        "passed": bool(preset and (preset in r.passed_presets)),
                        "matched_presets": r.passed_presets,
                    },
                },
            }
            for r in results
        ],
    }


@router.get("/presets")
async def get_presets() -> dict:
    from app.application.scanner.presets import list_presets
    return {"presets": list_presets()}
