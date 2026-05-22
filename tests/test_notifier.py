"""Tests for FakeNotifier (used as test double everywhere else)."""
from __future__ import annotations

import os

import pytest

from courant.notifier import DesktopNotifier, FakeNotifier


def test_fake_notifier_records_calls():
    n = FakeNotifier()
    n.notify(
        title="Water",
        body="Drink !",
        icon="💧",
        actions=[("ack", "Done"), ("snooze", "Snooze")],
        on_action=lambda a: None,
    )
    assert len(n.calls) == 1
    call = n.calls[0]
    assert call.title == "Water"
    assert call.body == "Drink !"
    assert call.icon == "💧"
    assert call.actions == [("ack", "Done"), ("snooze", "Snooze")]


def test_fake_notifier_trigger_action_calls_back():
    n = FakeNotifier()
    received: list[str] = []
    n.notify(
        title="t", body="b", icon=None,
        actions=[("ack", "OK")],
        on_action=lambda a: received.append(a),
    )
    n.trigger_action(0, "ack")
    assert received == ["ack"]


def test_fake_notifier_trigger_invalid_call_index_raises():
    n = FakeNotifier()
    with pytest.raises(IndexError):
        n.trigger_action(0, "ack")


@pytest.mark.skipif(
    not os.environ.get("DBUS_SESSION_BUS_ADDRESS"),
    reason="No D-Bus session available (CI usually skips this)",
)
def test_desktop_notifier_smoke():
    """Sends a real notification — only runs when D-Bus is around."""
    n = DesktopNotifier(app_name="courant-test")
    n.notify(
        title="Courant test",
        body="If you see this, D-Bus integration works.",
        icon=None,
        actions=[],
        on_action=lambda a: None,
    )
    # Nothing to assert programmatically — visual check only
