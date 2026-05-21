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
