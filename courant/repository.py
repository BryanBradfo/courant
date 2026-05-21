"""SQLite repository for Courant. Stdlib sqlite3 only, no ORM."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from courant.models import Reminder, format_active_days, format_time, parse_active_days, parse_time

SCHEMA_VERSION = 1

_MIGRATIONS: dict[int, str] = {
    1: """
        CREATE TABLE reminders (
            id                 INTEGER PRIMARY KEY,
            name               TEXT NOT NULL,
            message            TEXT NOT NULL,
            icon               TEXT,
            interval_minutes   INTEGER NOT NULL,
            active_hours_start TEXT NOT NULL DEFAULT '09:00',
            active_hours_end   TEXT NOT NULL DEFAULT '18:00',
            active_days        TEXT NOT NULL DEFAULT 'mon,tue,wed,thu,fri',
            enabled            INTEGER NOT NULL DEFAULT 1,
            tracked            INTEGER NOT NULL DEFAULT 0,
            unit_label         TEXT,
            unit_amount        INTEGER,
            daily_goal         INTEGER,
            created_at         TEXT NOT NULL,
            paused_until       TEXT
        );

        CREATE TABLE events (
            id          INTEGER PRIMARY KEY,
            reminder_id INTEGER NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
            occurred_at TEXT NOT NULL,
            kind        TEXT NOT NULL CHECK(kind IN ('fired', 'acked', 'snoozed', 'dismissed')),
            value       INTEGER
        );

        CREATE INDEX idx_events_reminder_time ON events(reminder_id, occurred_at);

        CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """,
}


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending migrations idempotently. Safe to call on every startup."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version in range(current + 1, SCHEMA_VERSION + 1):
        conn.executescript(_MIGRATIONS[version])
        conn.execute(f"PRAGMA user_version = {version}")
    conn.commit()


def _row_to_reminder(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        name=row["name"],
        message=row["message"],
        icon=row["icon"],
        interval_minutes=row["interval_minutes"],
        active_hours=(parse_time(row["active_hours_start"]), parse_time(row["active_hours_end"])),
        active_days=parse_active_days(row["active_days"]),
        enabled=bool(row["enabled"]),
        tracked=bool(row["tracked"]),
        unit_label=row["unit_label"],
        unit_amount=row["unit_amount"],
        daily_goal=row["daily_goal"],
        created_at=datetime.fromisoformat(row["created_at"]),
        paused_until=datetime.fromisoformat(row["paused_until"]) if row["paused_until"] else None,
    )


def insert_reminder(conn: sqlite3.Connection, r: Reminder) -> int:
    cursor = conn.execute(
        """
        INSERT INTO reminders (
            name, message, icon, interval_minutes,
            active_hours_start, active_hours_end, active_days,
            enabled, tracked, unit_label, unit_amount, daily_goal,
            created_at, paused_until
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            r.name, r.message, r.icon, r.interval_minutes,
            format_time(r.active_hours[0]), format_time(r.active_hours[1]),
            format_active_days(r.active_days),
            int(r.enabled), int(r.tracked),
            r.unit_label, r.unit_amount, r.daily_goal,
            r.created_at.isoformat(),
            r.paused_until.isoformat() if r.paused_until else None,
        ),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def get_reminder(conn: sqlite3.Connection, reminder_id: int) -> Reminder | None:
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    return _row_to_reminder(row) if row else None


def list_reminders(conn: sqlite3.Connection) -> list[Reminder]:
    rows = conn.execute("SELECT * FROM reminders ORDER BY id").fetchall()
    return [_row_to_reminder(row) for row in rows]


def update_reminder(conn: sqlite3.Connection, r: Reminder) -> None:
    if r.id is None:
        raise ValueError("Cannot update Reminder without id")
    conn.execute(
        """
        UPDATE reminders SET
            name = ?, message = ?, icon = ?, interval_minutes = ?,
            active_hours_start = ?, active_hours_end = ?, active_days = ?,
            enabled = ?, tracked = ?, unit_label = ?, unit_amount = ?, daily_goal = ?,
            paused_until = ?
        WHERE id = ?
        """,
        (
            r.name, r.message, r.icon, r.interval_minutes,
            format_time(r.active_hours[0]), format_time(r.active_hours[1]),
            format_active_days(r.active_days),
            int(r.enabled), int(r.tracked),
            r.unit_label, r.unit_amount, r.daily_goal,
            r.paused_until.isoformat() if r.paused_until else None,
            r.id,
        ),
    )
    conn.commit()


def delete_reminder(conn: sqlite3.Connection, reminder_id: int) -> None:
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()


def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with sane defaults for Courant."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
