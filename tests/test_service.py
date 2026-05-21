"""Tests for ReminderService (business logic)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, time

import pytest

from courant.models import Reminder, Weekday
from courant.repository import migrate
from courant.service import ReminderService


@pytest.fixture
def service(memory_db: sqlite3.Connection) -> ReminderService:
    migrate(memory_db)
    return ReminderService(conn=memory_db, snooze_minutes_default=10)


def _new_reminder(name: str = "Eau") -> Reminder:
    return Reminder(
        id=None,
        name=name,
        message="Hydrate-toi",
        icon="💧",
        interval_minutes=45,
        active_hours=(time(0, 0), time(23, 59)),
        active_days=frozenset(Weekday),
        enabled=True,
        tracked=True,
        unit_label="verre",
        unit_amount=250,
        daily_goal=8,
        created_at=datetime(2026, 5, 21, 10, 0),
        paused_until=None,
    )


def test_create_reminder_returns_id(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    assert rid > 0


def test_list_reminders(service: ReminderService):
    service.create_reminder(_new_reminder("A"))
    service.create_reminder(_new_reminder("B"))
    reminders = service.list_reminders()
    assert [r.name for r in reminders] == ["A", "B"]


def test_list_active_reminders_excludes_disabled(service: ReminderService):
    r = _new_reminder("Active")
    rid = service.create_reminder(r)
    r2 = _new_reminder("Disabled")
    r2.enabled = False
    service.create_reminder(r2)

    active = service.list_active_reminders()
    assert [a.id for a in active] == [rid]


def test_delete_reminder(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.delete_reminder(rid)
    assert service.get_reminder(rid) is None


from datetime import timedelta
from unittest.mock import MagicMock

from courant.repository import list_events_for_reminder


def test_is_in_active_window_inside(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(9, 0), time(18, 0))
    r.active_days = frozenset(Weekday)
    # Thursday 14:00
    now = datetime(2026, 5, 21, 14, 0)
    assert service.is_in_active_window(r, now) is True


def test_is_in_active_window_outside_hours(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(9, 0), time(18, 0))
    r.active_days = frozenset(Weekday)
    now = datetime(2026, 5, 21, 22, 0)
    assert service.is_in_active_window(r, now) is False


def test_is_in_active_window_wrong_day(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(0, 0), time(23, 59))
    r.active_days = frozenset({Weekday.MON})
    now = datetime(2026, 5, 21, 14, 0)  # Thursday
    assert service.is_in_active_window(r, now) is False


def test_fire_reminder_logs_event_and_calls_notifier(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    fake_notifier = MagicMock()
    service.fire_reminder(rid, notifier=fake_notifier, now=datetime(2026, 5, 21, 14, 0))

    events = list_events_for_reminder(service._conn, rid)
    assert len(events) == 1
    assert events[0].kind == "fired"
    fake_notifier.notify.assert_called_once()


def test_fire_reminder_skipped_when_outside_window(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(9, 0), time(18, 0))
    r.active_days = frozenset(Weekday)
    rid = service.create_reminder(r)

    fake_notifier = MagicMock()
    service.fire_reminder(rid, notifier=fake_notifier, now=datetime(2026, 5, 21, 22, 0))

    assert list_events_for_reminder(service._conn, rid) == []
    fake_notifier.notify.assert_not_called()


def test_fire_reminder_skipped_when_paused(service: ReminderService):
    r = _new_reminder()
    r.paused_until = datetime(2026, 5, 21, 16, 0)
    rid = service.create_reminder(r)

    fake_notifier = MagicMock()
    service.fire_reminder(rid, notifier=fake_notifier, now=datetime(2026, 5, 21, 14, 0))

    assert list_events_for_reminder(service._conn, rid) == []
    fake_notifier.notify.assert_not_called()


def test_fire_reminder_no_op_for_missing_reminder(service: ReminderService):
    fake_notifier = MagicMock()
    # Should not raise
    service.fire_reminder(999, notifier=fake_notifier, now=datetime(2026, 5, 21, 14, 0))
    fake_notifier.notify.assert_not_called()


def test_handle_action_ack_logs_event_with_unit_amount(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.handle_action(rid, "ack", now=datetime(2026, 5, 21, 14, 0))
    events = list_events_for_reminder(service._conn, rid)
    assert len(events) == 1
    assert events[0].kind == "acked"
    assert events[0].value == 250  # unit_amount from _new_reminder


def test_handle_action_ack_no_value_when_untracked(service: ReminderService):
    r = _new_reminder()
    r.tracked = False
    r.unit_amount = None
    rid = service.create_reminder(r)
    service.handle_action(rid, "ack")
    events = list_events_for_reminder(service._conn, rid)
    assert events[0].kind == "acked"
    assert events[0].value is None


def test_handle_action_snooze_logs_event(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.handle_action(rid, "snooze")
    events = list_events_for_reminder(service._conn, rid)
    assert events[-1].kind == "snoozed"


def test_handle_action_dismissed(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.handle_action(rid, "dismissed")
    events = list_events_for_reminder(service._conn, rid)
    assert events[-1].kind == "dismissed"


def test_handle_action_unknown_is_silently_ignored(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    # Should not raise
    service.handle_action(rid, "bogus")
    assert list_events_for_reminder(service._conn, rid) == []


def test_handle_action_missing_reminder_silently_ignored(service: ReminderService):
    # Should not raise
    service.handle_action(9999, "ack")


from courant.service import DailyProgress


def test_daily_progress_counts_acked_events_today(service: ReminderService):
    r = _new_reminder()
    r.daily_goal = 8
    rid = service.create_reminder(r)
    today = datetime(2026, 5, 21, 12, 0)

    # Today: 3 acked
    for h in [9, 10, 11]:
        service.handle_action(rid, "ack", now=today.replace(hour=h))
    # Yesterday: 5 acked (should not count)
    yesterday = today.replace(day=20)
    for h in [9, 10, 11, 12, 13]:
        service.handle_action(rid, "ack", now=yesterday.replace(hour=h))

    progress = service.daily_progress(rid, now=today)
    assert progress.count == 3
    assert progress.goal == 8
    assert progress.percent == pytest.approx(37.5)


def test_daily_progress_ignores_non_ack_events(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    today = datetime(2026, 5, 21, 12, 0)
    service.handle_action(rid, "snooze", now=today)
    service.handle_action(rid, "dismissed", now=today)
    progress = service.daily_progress(rid, now=today)
    assert progress.count == 0


def test_daily_progress_for_untracked_reminder_has_no_goal(service: ReminderService):
    r = _new_reminder()
    r.tracked = False
    r.daily_goal = None
    rid = service.create_reminder(r)
    progress = service.daily_progress(rid, now=datetime(2026, 5, 21, 12, 0))
    assert progress.goal is None
    assert progress.percent is None
