"""Business logic for Courant reminders.

ReminderService is the only place where domain logic lives. It owns a
sqlite3.Connection and delegates persistence to the repository module.
It does NOT know about notifications or scheduling - those are passed in
or called from outside (cli.py wires them together).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from courant.models import Reminder
from courant.repository import (
    delete_reminder,
    get_reminder,
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
