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
