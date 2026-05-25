"""In-process pub/sub bus for live UI events.

The daemon's scheduler runs reminders on a background thread (APScheduler).
The FastAPI app runs handlers on the asyncio event loop. This bus bridges
the two: scheduler threads call ``publish_threadsafe`` from anywhere, the
SSE endpoint subscribes from an asyncio handler and receives events on an
``asyncio.Queue``.

Design notes :
- One queue per subscriber. Slow consumer = own queue grows, others unaffected.
- ``publish_threadsafe`` is safe from any thread (uses
  ``loop.call_soon_threadsafe``). Calling before ``bind_loop`` is a no-op,
  which keeps unit tests of the scheduler simple (no event loop required).
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture the asyncio loop the FastAPI handlers run on.

        Must be called once at app startup (from the FastAPI lifespan
        handler). Before bind, ``publish_threadsafe`` is a no-op.
        """
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def publish_threadsafe(self, event: dict[str, Any]) -> None:
        """Fan out an event to every subscriber. Safe to call from any thread.

        Silently no-ops if no loop has been bound yet (e.g. CLI tests).
        """
        loop = self._loop
        if loop is None:
            return
        with self._lock:
            queues = list(self._subscribers)
        for q in queues:
            loop.call_soon_threadsafe(q.put_nowait, event)
