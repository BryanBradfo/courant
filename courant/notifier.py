"""Notification dispatch abstraction.

The Notifier protocol intentionally knows nothing about reminders, the DB,
or the scheduler. It just sends a (title, body, actions) tuple to whatever
backend is wired in. This lets tests use FakeNotifier without D-Bus, and
keeps future backends (web push, etc.) drop-in compatible.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

ActionId = str
ActionLabel = str
Action = tuple[ActionId, ActionLabel]
ActionCallback = Callable[[ActionId], None]


class Notifier(Protocol):
    def notify(
        self,
        title: str,
        body: str,
        icon: str | None,
        actions: list[Action],
        on_action: ActionCallback,
    ) -> None:
        ...


@dataclass
class _NotifyCall:
    title: str
    body: str
    icon: str | None
    actions: list[Action]
    on_action: ActionCallback


@dataclass
class FakeNotifier:
    """In-memory notifier for tests. Records calls and lets you trigger actions."""

    calls: list[_NotifyCall] = field(default_factory=list)

    def notify(
        self,
        title: str,
        body: str,
        icon: str | None,
        actions: list[Action],
        on_action: ActionCallback,
    ) -> None:
        self.calls.append(_NotifyCall(title, body, icon, actions, on_action))

    def trigger_action(self, call_index: int, action_id: ActionId) -> None:
        """Simulate the user clicking an action on a previously-sent notif."""
        self.calls[call_index].on_action(action_id)


import asyncio  # noqa: E402
import logging  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class DesktopNotifier:
    """Notifier backed by the `desktop-notifier` library (D-Bus on Linux).

    Uses an event loop running in a background thread so callbacks fire
    without blocking the scheduler.
    """

    app_name: str = "Courant"
    _loop: asyncio.AbstractEventLoop | None = field(default=None, init=False)
    _notifier: object | None = field(default=None, init=False)  # desktop_notifier.DesktopNotifier

    def __post_init__(self) -> None:
        # Lazy-import so tests/CI without the lib still parse this file
        import threading

        from desktop_notifier import DesktopNotifier as DN

        self._loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=self._loop.run_forever, daemon=True, name="courant-notif"
        )
        thread.start()
        self._notifier = DN(app_name=self.app_name)

    def notify(
        self,
        title: str,
        body: str,
        icon: str | None,
        actions: list[Action],
        on_action: ActionCallback,
    ) -> None:
        from desktop_notifier import Button

        buttons = [
            Button(title=label, on_pressed=lambda aid=aid: on_action(aid))  # type: ignore[misc]
            for aid, label in actions
        ]
        coro = self._notifier.send(  # type: ignore[attr-defined]
            title=title,
            message=body,
            buttons=buttons,
        )
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _log_error(fut: asyncio.Future[object]) -> None:
            exc = fut.exception()
            if exc:
                logger.warning("Notification failed: %s", exc)

        future.add_done_callback(_log_error)  # type: ignore[arg-type]
