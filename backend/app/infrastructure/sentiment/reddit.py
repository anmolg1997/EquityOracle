"""Reddit sentiment adapter (stub)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class RedditSentiment:
    ticker: str
    mentions: int
    sentiment_score: float  # -1 to 1
    bullish_pct: float
    source_subreddits: list[str]


async def get_reddit_sentiment(ticker: str) -> RedditSentiment | None:
    """Fetch Reddit sentiment for a stock.

    Stub — integrate with Reddit API or r/stocks, r/IndianStreetBets in production.
    """
    log.debug("reddit_sentiment_not_configured", ticker=ticker)
    return None
