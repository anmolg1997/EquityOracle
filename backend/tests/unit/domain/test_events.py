"""Tests for the in-process event bus."""

import pytest

from app.core.events import DomainEvent, EventBus


@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("test.event", handler)
    await bus.publish(DomainEvent(event_type="test.event", payload={"key": "value"}))

    assert len(received) == 1
    assert received[0].payload["key"] == "value"


@pytest.mark.asyncio
async def test_handler_error_does_not_propagate():
    bus = EventBus()

    async def bad_handler(event: DomainEvent):
        raise RuntimeError("handler failure")

    bus.subscribe("test.fail", bad_handler)
    await bus.publish(DomainEvent(event_type="test.fail"))


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("test.unsub", handler)
    bus.unsubscribe("test.unsub", handler)
    await bus.publish(DomainEvent(event_type="test.unsub"))

    assert len(received) == 0
