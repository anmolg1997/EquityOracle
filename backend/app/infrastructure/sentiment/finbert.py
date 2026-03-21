"""Local FinBERT model for news sentiment scoring."""

from __future__ import annotations

from app.core.logging import get_logger

log = get_logger(__name__)

_pipeline = None


def get_sentiment_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline
            _pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert", device=-1)
        except Exception as e:
            log.warning("finbert_load_failed", error=str(e))
    return _pipeline


def score_text(text: str) -> dict:
    """Score a text for financial sentiment using FinBERT.

    Returns: {"label": "positive"|"negative"|"neutral", "score": 0.0-1.0}
    """
    pipe = get_sentiment_pipeline()
    if pipe is None:
        return {"label": "neutral", "score": 0.5}

    try:
        result = pipe(text[:512])[0]
        return {"label": result["label"], "score": float(result["score"])}
    except Exception as e:
        log.error("finbert_scoring_failed", error=str(e))
        return {"label": "neutral", "score": 0.5}


def score_batch(texts: list[str]) -> list[dict]:
    """Score multiple texts efficiently."""
    return [score_text(t) for t in texts]
