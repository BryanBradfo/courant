"""Business logic for Courant reminders.

ReminderService is the only place where domain logic lives. It owns a
sqlite3.Connection and delegates persistence to the repository module.
It does NOT know about notifications or scheduling - those are passed in
or called from outside (cli.py wires them together).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime

from courant.models import Event, Reminder, Weekday
from courant.repository import (
    delete_reminder,
    get_reminder,
    insert_event,
    insert_reminder,
    list_reminders,
    update_reminder,
)


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
        notifier,  # Notifier protocol — typed in Task 12
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

    def handle_action(self, reminder_id: int, action_id: str) -> None:
        # Implemented in Task 10
        raise NotImplementedError
