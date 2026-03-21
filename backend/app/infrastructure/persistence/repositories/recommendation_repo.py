"""Recommendation repository — stores and retrieves recommendations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

log = get_logger(__name__)


class SQLRecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
