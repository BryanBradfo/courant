"""Tests for the in-process pub/sub bus used for live UI events."""
from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from courant.events_bus import EventBus


@pytest.mark.asyncio
async def test_publish_threadsafe_no_loop_is_no_op() -> None:
    """Before bind_loop, publish_threadsafe must not raise."""
    bus = EventBus()
    bus.publish_threadsafe({"type": "noop"})  # no exception, no effect


@pytest.mark.asyncio
async def test_subscribe_receives_published_events_same_thread() -> None:
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    q = bus.subscribe()
    bus.publish_threadsafe({"type": "reminder_fired", "id": 1})

    event = await asyncio.wait_for(q.get(), timeout=1.0)
    assert event == {"type": "reminder_fired", "id": 1}


@pytest.mark.asyncio
async def test_fans_out_to_multiple_subscribers() -> None:
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    bus.publish_threadsafe({"type": "ping"})

    assert (await asyncio.wait_for(q1.get(), timeout=1.0))["type"] == "ping"
    assert (await asyncio.wait_for(q2.get(), timeout=1.0))["type"] == "ping"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    bus.unsubscribe(q1)

    bus.publish_threadsafe({"type": "ping"})
    assert (await asyncio.wait_for(q2.get(), timeout=1.0))["type"] == "ping"
    assert q1.empty()


@pytest.mark.asyncio
async def test_publish_from_background_thread_reaches_subscriber() -> None:
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    q = bus.subscribe()

    def producer() -> None:
        bus.publish_threadsafe({"type": "from_thread", "value": 42})

    t = threading.Thread(target=producer)
    t.start()
    t.join()

    event: dict[str, Any] = await asyncio.wait_for(q.get(), timeout=1.0)
    assert event == {"type": "from_thread", "value": 42}


@pytest.mark.asyncio
async def test_subscriber_count_tracks_lifecycle() -> None:
    bus = EventBus()
    assert bus.subscriber_count() == 0
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    assert bus.subscriber_count() == 2
    bus.unsubscribe(q1)
    assert bus.subscriber_count() == 1
    bus.unsubscribe(q2)
    assert bus.subscriber_count() == 0
