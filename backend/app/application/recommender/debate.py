"""Bull/Bear debate orchestration via LLM."""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.types import Ticker
from app.domain.recommendation.models import DebateResult, SignalDirection
from app.infrastructure.llm.base import LLMProvider
from app.infrastructure.llm.cost_tracker import LLMCostTracker

log = get_logger(__name__)

DEBATE_SYSTEM = """You are a senior equity analyst conducting a structured investment debate.
Provide evidence-based analysis grounded in the data provided. Be specific about numbers and ratios.
Keep each section concise (2-3 paragraphs max)."""


async def run_debate(
    ticker: Ticker,
    context: dict,
    llm: LLMProvider,
    cost_tracker: LLMCostTracker,
) -> DebateResult:
    """Run a Bull/Bear/Synthesis debate for a stock.

    Only called for top 10-15 stocks by composite score to control costs.
    """
    if not cost_tracker.can_afford(estimated_cost=0.5):
        log.info("debate_skipped_budget", ticker=str(ticker))
        return DebateResult(ticker=ticker, synthesis="Budget exhausted — debate deferred")

    prompt = f"""Analyze {ticker.symbol} ({ticker.exchange.value}) for investment potential.

Data context:
- Technical Score: {context.get('technical_score', 'N/A')}
- Factor Score: {context.get('factor_score', 'N/A')}
- PE Ratio: {context.get('pe_ratio', 'N/A')}
- Sector: {context.get('sector', 'N/A')}

Provide your analysis in this exact format:
BULL CASE:
[Your bullish argument]

BEAR CASE:
[Your bearish argument]

SYNTHESIS:
[Your balanced verdict with probability assessment]

VERDICT: [BUY/SELL/HOLD]"""

    try:
        response = await llm.generate(prompt, system=DEBATE_SYSTEM)

        cost_tracker.record_usage(
            model=llm.model_name,
            input_tokens=len(prompt.split()) * 2,
            output_tokens=len(response.split()) * 2,
            purpose="debate",
        )

        return _parse_debate(ticker, response)

    except Exception as e:
        log.error("debate_failed", ticker=str(ticker), error=str(e))
        return DebateResult(ticker=ticker, synthesis=f"Debate failed: {e}")


def _parse_debate(ticker: Ticker, response: str) -> DebateResult:
    result = DebateResult(ticker=ticker)

    sections = response.upper()
    if "BULL CASE:" in sections:
        start = response.upper().index("BULL CASE:") + len("BULL CASE:")
        end = response.upper().index("BEAR CASE:") if "BEAR CASE:" in sections else len(response)
        result.bull_case = response[start:end].strip()

    if "BEAR CASE:" in sections:
        start = response.upper().index("BEAR CASE:") + len("BEAR CASE:")
        end = response.upper().index("SYNTHESIS:") if "SYNTHESIS:" in sections else len(response)
        result.bear_case = response[start:end].strip()

    if "SYNTHESIS:" in sections:
        start = response.upper().index("SYNTHESIS:") + len("SYNTHESIS:")
        end = response.upper().index("VERDICT:") if "VERDICT:" in sections else len(response)
        result.synthesis = response[start:end].strip()

    if "VERDICT:" in sections:
        verdict_text = response[response.upper().index("VERDICT:") + len("VERDICT:"):].strip().upper()
        if "BUY" in verdict_text:
            result.verdict = SignalDirection.BUY
        elif "SELL" in verdict_text:
            result.verdict = SignalDirection.SELL
        else:
            result.verdict = SignalDirection.HOLD

    return result
