"""Recommender service — orchestrates scoring, prediction, and recommendation."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.core.logging import get_logger
from app.core.observability import trace_span
from app.core.types import Market, Ticker, TimeHorizon, new_correlation_id
from app.domain.analysis.composite import compute_composite
from app.domain.analysis.factors import compute_factor_scores
from app.domain.analysis.models import CompositeScore
from app.domain.analysis.technical import compute_technical_score
from app.domain.market_data.ports import MarketDataProvider, MarketDataRepository
from app.domain.recommendation.exit_signals import generate_exit_rules
from app.domain.recommendation.models import DecisionAudit, Recommendation, Signal, SignalDirection
from app.domain.recommendation.scoring import generate_multi_horizon_signals

log = get_logger(__name__)


class RecommenderService:
    """Generates recommendations with full audit trail."""

    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository,
    ) -> None:
        self._provider = provider
        self._repo = repository

    async def generate_recommendations(
        self,
        market: Market = Market.INDIA,
        horizons: list[TimeHorizon] | None = None,
        limit: int = 20,
    ) -> list[Recommendation]:
        """Generate ranked recommendations for the given market and horizons."""
        correlation_id = new_correlation_id()
        horizons = horizons or [TimeHorizon.DAY_1, TimeHorizon.DAY_3, TimeHorizon.WEEK_1, TimeHorizon.MONTH_1]

        with trace_span("recommender.generate", correlation_id=correlation_id):
            tickers = await self._repo.get_universe(market)
            if not tickers:
                tickers = await self._provider.get_universe(market)

            recommendations: list[Recommendation] = []
            end = date.today()
            start = end - timedelta(days=365)

            for ticker in tickers[:200]:
                try:
                    rec = await self._score_ticker(ticker, start, end, horizons, correlation_id)
                    if rec:
                        recommendations.append(rec)
                except Exception as e:
                    log.debug("recommendation_failed", ticker=str(ticker), error=str(e))

            # Sort by best signal strength, filter to BUY signals
            buy_recs = [r for r in recommendations if r.signal.direction == SignalDirection.BUY]
            buy_recs.sort(key=lambda r: r.signal.strength, reverse=True)

            return buy_recs[:limit]

    async def _score_ticker(
        self,
        ticker: Ticker,
        start: date,
        end: date,
        horizons: list[TimeHorizon],
        correlation_id: str,
    ) -> Recommendation | None:
        ohlcv = await self._repo.get_ohlcv(ticker, start, end)
        if not ohlcv or len(ohlcv) < 50:
            return None

        tech = compute_technical_score(ticker, ohlcv)
        fundamentals = await self._repo.get_fundamentals(ticker)
        factors = compute_factor_scores(ticker, ohlcv, fundamentals)

        composite = compute_composite(
            ticker=ticker,
            technical=tech,
            factor=factors,
        )

        # Generate signals for each horizon (using composite as proxy until ML is trained)
        horizon_preds = {
            h: {"expected_return": float(composite.overall - 50) / 10, "confidence": float(composite.overall) / 100}
            for h in horizons
        }
        signals = generate_multi_horizon_signals(
            ticker=ticker,
            composite_score=composite.overall,
            horizon_predictions=horizon_preds,
            effective_signal_count=composite.effective_signal_count,
        )

        if not signals:
            return None

        best_signal = max(signals, key=lambda s: s.strength)

        entry_price = ohlcv[-1].close
        atr = tech.atr_14
        exit_rules = generate_exit_rules(entry_price, atr)

        audit = DecisionAudit(
            correlation_id=correlation_id,
            ticker=ticker,
            horizon=best_signal.horizon,
            decision=best_signal.direction,
            technical_score=tech.score,
            factor_score=factors.composite,
            composite_score=composite.overall,
            confidence=best_signal.confidence,
            weights_used=composite.weights_used,
            pillar_correlations=composite.pillar_correlations,
            effective_signal_count=composite.effective_signal_count,
        )

        return Recommendation(
            signal=best_signal,
            exit_rules=exit_rules,
            audit=audit,
        )
