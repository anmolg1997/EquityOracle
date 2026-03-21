"""NewsAPI adapter for fetching financial news."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class NewsArticle:
    title: str
    description: str
    source: str
    url: str
    published_at: str


async def fetch_news(query: str, api_key: str, days: int = 7) -> list[NewsArticle]:
    """Fetch news articles for a stock or topic."""
    if not api_key:
        return []

    try:
        from newsapi import NewsApiClient
        client = NewsApiClient(api_key=api_key)
        results = client.get_everything(q=query, language="en", sort_by="relevancy", page_size=20)

        articles: list[NewsArticle] = []
        for article in results.get("articles", []):
            articles.append(NewsArticle(
                title=article.get("title", ""),
                description=article.get("description", ""),
                source=article.get("source", {}).get("name", ""),
                url=article.get("url", ""),
                published_at=article.get("publishedAt", ""),
            ))
        return articles

    except Exception as e:
        log.error("news_fetch_failed", query=query, error=str(e))
        return []
