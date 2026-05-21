"""Business logic for Courant reminders.

ReminderService is the only place where domain logic lives. It owns a
sqlite3.Connection and delegates persistence to the repository module.
It does NOT know about notifications or scheduling - those are passed in
or called from outside (cli.py wires them together).
"""
from __future__ import annotations

import importlib.resources
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from courant.models import Event, Reminder, Weekday, parse_active_days, parse_time
from courant.notifier import Notifier
from courant.repository import (
    delete_reminder,
    get_reminder,
    insert_event,
    insert_reminder,
    list_events_in_range,
    list_reminders,
    update_reminder,
)


@dataclass
class DailyProgress:
    reminder_id: int
    count: int
    goal: int | None
    percent: float | None


class ReminderService:
    def __init__(self, conn: sqlite3.Connection, snooze_minutes_default: int = 10) -> None:
        self._conn = conn
        self._snooze_minutes_default = snooze_minutes_default

    # ----- CRUD -----

    def create_reminder(self, reminder: Reminder) -> int:
        reminder.created_at = reminder.created_at or datetime.now()
        return insert_reminder(self._conn, reminder)

    def get_reminder(self, reminder_id: int) -> Reminder | None:
        return get_reminder(self._conn, reminder_id)

    def list_reminders(self) -> list[Reminder]:
        return list_reminders(self._conn)

    def list_active_reminders(self) -> list[Reminder]:
        """Enabled reminders (paused or not — caller decides what to do)."""
        return [r for r in list_reminders(self._conn) if r.enabled]

    def update_reminder(self, reminder: Reminder) -> None:
        update_reminder(self._conn, reminder)

    def delete_reminder(self, reminder_id: int) -> None:
        delete_reminder(self._conn, reminder_id)

    # ----- Active window -----

    _WEEKDAY_BY_INDEX = (
        Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU,
        Weekday.FRI, Weekday.SAT, Weekday.SUN,
    )

    def is_in_active_window(self, r: Reminder, now: datetime) -> bool:
        weekday = self._WEEKDAY_BY_INDEX[now.weekday()]
        if weekday not in r.active_days:
            return False
        start, end = r.active_hours
        current = now.time()
        return start <= current <= end

    def fire_reminder(
        self,
        reminder_id: int,
        notifier: Notifier,
        now: datetime | None = None,
    ) -> None:
        """Trigger a notification for this reminder, if conditions allow.

        Logs a 'fired' event and dispatches to notifier. Silently no-ops when:
        - reminder doesn't exist
        - reminder is paused
        - now is outside active window
        """
        now = now or datetime.now()
        r = self.get_reminder(reminder_id)
        if r is None or not r.enabled:
            return
        if r.paused_until and now < r.paused_until:
            return
        if not self.is_in_active_window(r, now):
            return

        insert_event(self._conn, Event(
            id=None,
            reminder_id=reminder_id,
            occurred_at=now,
            kind="fired",
            value=None,
        ))

        notifier.notify(
            title=r.name,
            body=r.message,
            icon=r.icon,
            actions=self._actions_for(r),
            on_action=lambda action_id: self.handle_action(reminder_id, action_id),
        )

    def _actions_for(self, r: Reminder) -> list[tuple[str, str]]:
        actions = []
        if r.tracked:
            label = f"+1 {r.unit_label}" if r.unit_label else "Fait ✓"
            actions.append(("ack", label))
        else:
            actions.append(("ack", "OK"))
        actions.append(("snooze", f"Snooze {self._snooze_minutes_default}min"))
        return actions

    def handle_action(
        self,
        reminder_id: int,
        action_id: str,
        now: datetime | None = None,
    ) -> None:
        """Process a user action on a notification.

        Known actions: 'ack', 'snooze', 'dismissed'. Unknown actions are
        silently ignored to be forward-compatible with future notifier impls.
        """
        if action_id not in ("ack", "snooze", "dismissed"):
            return

        now = now or datetime.now()
        r = self.get_reminder(reminder_id)
        if r is None:
            return  # Reminder was deleted between notif and click

        kind_map = {"ack": "acked", "snooze": "snoozed", "dismissed": "dismissed"}
        kind = kind_map[action_id]
        value = r.unit_amount if kind == "acked" and r.tracked else None

        insert_event(self._conn, Event(
            id=None,
            reminder_id=reminder_id,
            occurred_at=now,
            kind=kind,  # type: ignore[arg-type]
            value=value,
        ))

    def seed_defaults_if_empty(self) -> int:
        """Seed default reminders from data/default_reminders.json if no reminders exist.

        Returns the number of reminders seeded (0 if DB already had reminders).
        """
        if list_reminders(self._conn):
            return 0

        ref = importlib.resources.files("courant.data").joinpath("default_reminders.json")
        with ref.open("r", encoding="utf-8") as fh:
            entries = json.load(fh)

        count = 0
        for entry in entries:
            reminder = Reminder(
                id=None,
                name=entry["name"],
                message=entry["message"],
                icon=entry.get("icon"),
                interval_minutes=entry["interval_minutes"],
                active_hours=(
                    parse_time(entry["active_hours_start"]),
                    parse_time(entry["active_hours_end"]),
                ),
                active_days=parse_active_days(entry["active_days"]),
                enabled=True,
                tracked=entry.get("tracked", False),
                unit_label=entry.get("unit_label"),
                unit_amount=entry.get("unit_amount"),
                daily_goal=entry.get("daily_goal"),
                created_at=datetime.now(),
                paused_until=None,
            )
            self.create_reminder(reminder)
            count += 1
        return count

    def daily_progress(self, reminder_id: int, now: datetime | None = None) -> DailyProgress:
        now = now or datetime.now()
        r = self.get_reminder(reminder_id)
        if r is None:
            return DailyProgress(reminder_id, 0, None, None)

        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        events = list_events_in_range(self._conn, start, end, reminder_id=reminder_id)
        count = sum(1 for e in events if e.kind == "acked")
        goal = r.daily_goal if r.tracked else None
        percent = (count / goal * 100) if (goal and goal > 0) else None
        return DailyProgress(reminder_id, count, goal, percent)
