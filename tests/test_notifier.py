"""Tests for FakeNotifier (used as test double everywhere else)."""
from __future__ import annotations

from courant.notifier import FakeNotifier


def test_fake_notifier_records_calls():
    n = FakeNotifier()
    n.notify(
        title="Eau",
        body="Bois !",
        icon="💧",
        actions=[("ack", "Fait"), ("snooze", "Snooze")],
        on_action=lambda a: None,
    )
    assert len(n.calls) == 1
    call = n.calls[0]
    assert call.title == "Eau"
    assert call.body == "Bois !"
    assert call.icon == "💧"
    assert call.actions == [("ack", "Fait"), ("snooze", "Snooze")]


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
    import pytest
    with pytest.raises(IndexError):
        n.trigger_action(0, "ack")
