"""In-process async event bus for domain event propagation."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

EventHandler = Callable[["DomainEvent"], Coroutine[Any, Any, None]]


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Simple in-process pub/sub for decoupled domain event handling.

    Not a replacement for a message broker — this is for same-process
    notification (audit logging, cache invalidation, alerts).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type] = [h for h in self._handlers[event_type] if h is not handler]

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Event handler %s failed for %s: %s",
                    handlers[i].__qualname__,
                    event.event_type,
                    result,
                )


event_bus = EventBus()
