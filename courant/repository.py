"""SQLite repository for Courant. Stdlib sqlite3 only, no ORM."""
from __future__ import annotations

import sqlite3

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


def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with sane defaults for Courant."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
