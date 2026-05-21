"""Tests for SQLite repository."""
from __future__ import annotations

import sqlite3
from datetime import datetime, time

from courant.models import Event, Reminder, Weekday
from courant.repository import (
    SCHEMA_VERSION,
    delete_reminder,
    get_reminder,
    insert_event,
    insert_reminder,
    list_events_for_reminder,
    list_events_in_range,
    list_reminders,
    migrate,
    update_reminder,
)


def test_migrate_creates_all_tables(memory_db: sqlite3.Connection):
    migrate(memory_db)
    tables = {
        row["name"]
        for row in memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "reminders" in tables
    assert "events" in tables
    assert "settings" in tables


def test_migrate_sets_user_version(memory_db: sqlite3.Connection):
    migrate(memory_db)
    version = memory_db.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_migrate_is_idempotent(memory_db: sqlite3.Connection):
    migrate(memory_db)
    migrate(memory_db)  # Should not raise
    version = memory_db.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION


def test_migrate_creates_event_index(memory_db: sqlite3.Connection):
    migrate(memory_db)
    indexes = {
        row["name"]
        for row in memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
    }
    assert "idx_events_reminder_time" in indexes


def _sample_reminder(name: str = "Eau") -> Reminder:
    return Reminder(
        id=None,
        name=name,
        message="Hydrate-toi",
        icon="💧",
        interval_minutes=45,
        active_hours=(time(9, 0), time(18, 0)),
        active_days=frozenset({Weekday.MON, Weekday.TUE}),
        enabled=True,
        tracked=True,
        unit_label="verre",
        unit_amount=250,
        daily_goal=8,
        created_at=datetime(2026, 5, 21, 10, 0),
        paused_until=None,
    )


def test_insert_and_get_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    reminder = _sample_reminder()
    new_id = insert_reminder(memory_db, reminder)
    assert new_id > 0
    fetched = get_reminder(memory_db, new_id)
    assert fetched is not None
    assert fetched.name == "Eau"
    assert fetched.interval_minutes == 45
    assert fetched.icon == "💧"
    assert fetched.active_days == frozenset({Weekday.MON, Weekday.TUE})


def test_get_reminder_missing_returns_none(memory_db: sqlite3.Connection):
    migrate(memory_db)
    assert get_reminder(memory_db, 9999) is None


def test_list_reminders_orders_by_id(memory_db: sqlite3.Connection):
    migrate(memory_db)
    id_a = insert_reminder(memory_db, _sample_reminder("A"))
    id_b = insert_reminder(memory_db, _sample_reminder("B"))
    reminders = list_reminders(memory_db)
    assert [r.id for r in reminders] == [id_a, id_b]


def test_update_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    rid = insert_reminder(memory_db, _sample_reminder())
    fetched = get_reminder(memory_db, rid)
    assert fetched is not None
    fetched.interval_minutes = 60
    fetched.enabled = False
    update_reminder(memory_db, fetched)
    reloaded = get_reminder(memory_db, rid)
    assert reloaded is not None
    assert reloaded.interval_minutes == 60
    assert reloaded.enabled is False


def test_delete_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    rid = insert_reminder(memory_db, _sample_reminder())
    delete_reminder(memory_db, rid)
    assert get_reminder(memory_db, rid) is None


def test_insert_event_assigns_id(memory_db: sqlite3.Connection):
    migrate(memory_db)
    rid = insert_reminder(memory_db, _sample_reminder())
    eid = insert_event(memory_db, Event(
        id=None,
        reminder_id=rid,
        occurred_at=datetime(2026, 5, 21, 14, 0),
        kind="fired",
        value=None,
    ))
    assert eid > 0


def test_list_events_for_reminder_returns_in_order(memory_db: sqlite3.Connection):
    migrate(memory_db)
    rid = insert_reminder(memory_db, _sample_reminder())
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 21, 9, 0), "fired", None))
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 21, 10, 0), "acked", 250))
    events = list_events_for_reminder(memory_db, rid)
    assert len(events) == 2
    assert events[0].kind == "fired"
    assert events[1].kind == "acked"
    assert events[1].value == 250


def test_list_events_in_range_excludes_outside(memory_db: sqlite3.Connection):
    migrate(memory_db)
    rid = insert_reminder(memory_db, _sample_reminder())
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 20, 23, 0), "fired", None))
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 21, 9, 0), "fired", None))
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 21, 23, 0), "fired", None))
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 22, 0, 1), "fired", None))
    events = list_events_in_range(
        memory_db,
        start=datetime(2026, 5, 21, 0, 0),
        end=datetime(2026, 5, 22, 0, 0),
    )
    assert len(events) == 2


def test_delete_reminder_cascades_to_events(memory_db: sqlite3.Connection):
    migrate(memory_db)
    rid = insert_reminder(memory_db, _sample_reminder())
    insert_event(memory_db, Event(None, rid, datetime(2026, 5, 21, 14, 0), "fired", None))
    delete_reminder(memory_db, rid)
    events = list_events_for_reminder(memory_db, rid)
    assert events == []
