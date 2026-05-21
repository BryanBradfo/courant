"""Tests for SQLite repository."""
from __future__ import annotations

import sqlite3

from courant.repository import SCHEMA_VERSION, migrate


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
