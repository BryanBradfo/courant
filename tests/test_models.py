"""Tests for Reminder and Event dataclasses."""
from __future__ import annotations

from datetime import datetime, time

from courant.models import Event, Reminder, Weekday, parse_active_days


def test_reminder_construction_minimal():
    r = Reminder(
        id=None,
        name="Water",
        message="Drink !",
        icon=None,
        interval_minutes=45,
        active_hours=(time(9, 0), time(18, 0)),
        active_days=frozenset({Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI}),
        enabled=True,
        tracked=False,
        unit_label=None,
        unit_amount=None,
        daily_goal=None,
        created_at=datetime(2026, 5, 21, 14, 0),
        paused_until=None,
    )
    assert r.name == "Water"
    assert r.interval_minutes == 45
    assert r.enabled is True


def test_parse_active_days_full_week():
    days = parse_active_days("mon,tue,wed,thu,fri,sat,sun")
    assert days == frozenset(Weekday)


def test_parse_active_days_weekdays_only():
    days = parse_active_days("mon,tue,wed,thu,fri")
    assert Weekday.MON in days
    assert Weekday.SAT not in days


def test_parse_active_days_handles_whitespace():
    days = parse_active_days(" mon , tue , wed ")
    assert days == frozenset({Weekday.MON, Weekday.TUE, Weekday.WED})


def test_event_kind_typed():
    e = Event(
        id=None,
        reminder_id=1,
        occurred_at=datetime(2026, 5, 21, 14, 30),
        kind="acked",
        value=250,
    )
    assert e.kind == "acked"
    assert e.value == 250
