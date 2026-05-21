"""Dataclasses for Courant domain objects.

These mirror the SQLite schema but are the canonical in-memory representation
used by service.py. Repository handles the conversion to/from rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum
from typing import Literal


class Weekday(StrEnum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


EventKind = Literal["fired", "acked", "snoozed", "dismissed"]


@dataclass
class Reminder:
    id: int | None
    name: str
    message: str
    icon: str | None
    interval_minutes: int
    active_hours: tuple[time, time]
    active_days: frozenset[Weekday]
    enabled: bool
    tracked: bool
    unit_label: str | None
    unit_amount: int | None
    daily_goal: int | None
    created_at: datetime
    paused_until: datetime | None


@dataclass
class Event:
    id: int | None
    reminder_id: int
    occurred_at: datetime
    kind: EventKind
    value: int | None


def parse_active_days(csv: str) -> frozenset[Weekday]:
    """Parse 'mon,tue,wed' style CSV into a Weekday set."""
    parts = [p.strip().lower() for p in csv.split(",") if p.strip()]
    return frozenset(Weekday(p) for p in parts)


def format_active_days(days: frozenset[Weekday]) -> str:
    """Inverse of parse_active_days, with stable ordering."""
    ordered = [d.value for d in Weekday if d in days]
    return ",".join(ordered)


def parse_time(hhmm: str) -> time:
    """Parse 'HH:MM' string into a datetime.time."""
    hour, minute = hhmm.split(":")
    return time(int(hour), int(minute))


def format_time(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"
