# Courant — Phase 1 (Core fonctionnel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working CLI-only reminder daemon that fires desktop notifications on schedule, with full data persistence and tests. No web UI yet.

**Architecture:** Single Python process. `cli.py` boots the daemon. `scheduler.py` (APScheduler) periodically calls `service.fire_reminder`. `service.py` (business logic) checks active windows, logs events via `repository.py` (SQLite), and dispatches to `notifier.py` (desktop-notifier lib over D-Bus). Strict layering: `notifier` and `repository` know nothing about each other; `service` orchestrates.

**Tech Stack:** Python 3.11+, `sqlite3` (stdlib), `apscheduler`, `desktop-notifier`, `pytest`, `freezegun`, `ruff`, `mypy`. No web framework yet (Phase 2). No ORM.

**Phase 1 scope (this plan):**
- Project bootstrap (pyproject.toml, package layout, tooling)
- `models.py` — Reminder & Event dataclasses
- `repository.py` — SQLite CRUD + migrations + backups
- `notifier.py` — Protocol + FakeNotifier + DesktopNotifier impl
- `service.py` — business logic
- `scheduler.py` — APScheduler integration
- `cli.py` — `courant start/stop/status/version`
- `default_reminders.json` seed on first launch

**Out of scope (later phases):**
- Web UI / FastAPI (Phase 2)
- Glassmorphism, scenes, ambient sounds (Phase 3)
- systemd service, README polish, PyPI publish (Phase 4)

---

## File Structure

```
courant/                                # repo root (already exists, git init done)
├── pyproject.toml                      # Task 1 — create
├── .gitignore                          # Task 1 — create
├── LICENSE                             # Task 1 — create
├── README.md                           # Task 1 — create (skeleton)
├── courant/                            # Python package
│   ├── __init__.py                     # Task 1 — create
│   ├── models.py                       # Task 2 — create
│   ├── repository.py                   # Tasks 3-7 — create + grow
│   ├── service.py                      # Tasks 8-11 — create + grow
│   ├── notifier.py                     # Tasks 12-13 — create + grow
│   ├── scheduler.py                    # Tasks 14-15 — create + grow
│   ├── cli.py                          # Tasks 16-19 — create + grow
│   ├── paths.py                        # Task 1 — create (XDG path helpers)
│   └── data/
│       └── default_reminders.json      # Task 20 — create
└── tests/
    ├── __init__.py                     # Task 1
    ├── conftest.py                     # Task 1 (shared fixtures)
    ├── test_models.py                  # Task 2
    ├── test_repository.py              # Tasks 3-7
    ├── test_service.py                 # Tasks 8-11
    ├── test_notifier.py                # Task 12
    ├── test_scheduler.py               # Tasks 14-15
    └── test_cli.py                     # Tasks 16-20
```

**Boundaries (recap from spec):**
- `notifier.py` ignores DB — takes `(title, body, actions, callback)`
- `scheduler.py` ignores HTTP — consumes `service` + `notifier`
- `repository.py` is the only module that imports `sqlite3`
- `service.py` is the only module business logic lives in
- `cli.py` wires everything together at startup

---

## Task 1: Bootstrap project

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`
- Create: `courant/__init__.py`, `courant/paths.py`
- Create: `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/

# Virtual envs
.venv/
venv/

# Editor
.vscode/
.idea/
*.swp

# Courant runtime (should never be in repo)
courant/static/sounds/

# OS
.DS_Store
```

- [ ] **Step 2: Create `LICENSE` (MIT)**

```
MIT License

Copyright (c) 2026 Bryan Chen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "courant"
version = "0.1.0"
description = "Un rappel cozy pour les devs : eau, yeux, étirements."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Bryan Chen", email = "bryan.chen@wingleet.com" },
]
dependencies = [
    "apscheduler>=3.10",
    "desktop-notifier>=4.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "freezegun>=1.4",
    "ruff>=0.4",
    "mypy>=1.10",
]

[project.scripts]
courant = "courant.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["courant"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
```

- [ ] **Step 4: Create `README.md` skeleton**

```markdown
# Courant

> Un rappel cozy pour les devs : eau, yeux, étirements.

Linux desktop app that sends customizable notifications to remind you to drink water, rest your eyes, stretch — with a cozy lo-fi web interface (coming in Phase 2).

**Status:** Early development. Phase 1 complete = CLI + notifications work. Phase 2 will add the web UI.

## Install (dev)

    git clone https://github.com/<user>/courant
    cd courant
    pip install -e ".[dev]"
    courant start

## License

MIT
```

- [ ] **Step 5: Create empty package files**

`courant/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/__init__.py`: empty file.

- [ ] **Step 6: Create `courant/paths.py`**

```python
"""XDG Base Directory paths for Courant runtime data."""
from __future__ import annotations

import os
from pathlib import Path


def _xdg(env_var: str, default_subpath: str) -> Path:
    base = os.environ.get(env_var)
    if base:
        return Path(base)
    return Path.home() / default_subpath


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "courant"


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "courant"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "courant"


def db_path() -> Path:
    return data_dir() / "courant.db"


def log_path() -> Path:
    return cache_dir() / "logs" / "courant.log"


def ensure_dirs() -> None:
    for d in (config_dir(), data_dir(), cache_dir(), cache_dir() / "logs"):
        d.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 7: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all XDG paths to a temp directory for the test."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path


@pytest.fixture
def memory_db() -> Iterator[sqlite3.Connection]:
    """In-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()
```

- [ ] **Step 8: Install dev deps and verify**

Run:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

Expected: pytest reports `no tests ran in X.XXs` (exits 5 — no tests collected, OK).

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .gitignore LICENSE README.md courant/ tests/
git commit -m "feat: bootstrap project structure (pyproject, paths, tooling)"
```

---

## Task 2: `models.py` — Reminder & Event dataclasses

**Files:**
- Create: `courant/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

`tests/test_models.py`:
```python
"""Tests for Reminder and Event dataclasses."""
from __future__ import annotations

from datetime import datetime, time

from courant.models import Event, Reminder, Weekday, parse_active_days


def test_reminder_construction_minimal():
    r = Reminder(
        id=None,
        name="Eau",
        message="Bois !",
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
    assert r.name == "Eau"
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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: `ModuleNotFoundError: No module named 'courant.models'`

- [ ] **Step 3: Implement `courant/models.py`**

```python
"""Dataclasses for Courant domain objects.

These mirror the SQLite schema but are the canonical in-memory representation
used by service.py. Repository handles the conversion to/from rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Literal


class Weekday(str, Enum):
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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/models.py tests/test_models.py
git commit -m "feat(models): add Reminder, Event dataclasses + day/time parsers"
```

---

## Task 3: `repository.py` — schema + migrations

**Files:**
- Create: `courant/repository.py`
- Test: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests**

`tests/test_repository.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_repository.py -v`
Expected: ImportError on `courant.repository`.

- [ ] **Step 3: Implement migrations in `courant/repository.py`**

```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_repository.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/repository.py tests/test_repository.py
git commit -m "feat(repo): SQLite schema + idempotent migrations"
```

---

## Task 4: `repository.py` — Reminder CRUD

**Files:**
- Modify: `courant/repository.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests (append to `tests/test_repository.py`)**

```python
from datetime import datetime, time
from courant.models import Reminder, Weekday
from courant.repository import (
    delete_reminder,
    get_reminder,
    insert_reminder,
    list_reminders,
    update_reminder,
)


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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_repository.py -v -k reminder`
Expected: ImportError on the new functions.

- [ ] **Step 3: Implement Reminder CRUD (append to `courant/repository.py`)**

```python
from datetime import datetime
from courant.models import Reminder, format_active_days, format_time, parse_active_days, parse_time


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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_repository.py -v`
Expected: all reminder tests pass (5 new + 4 from Task 3 = 9 total).

- [ ] **Step 5: Commit**

```bash
git add courant/repository.py tests/test_repository.py
git commit -m "feat(repo): Reminder CRUD"
```

---

## Task 5: `repository.py` — Event insert + queries

**Files:**
- Modify: `courant/repository.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests (append to `tests/test_repository.py`)**

```python
from courant.models import Event
from courant.repository import insert_event, list_events_for_reminder, list_events_in_range


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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_repository.py -v -k event`
Expected: ImportError on event functions.

- [ ] **Step 3: Implement event functions (append to `courant/repository.py`)**

```python
from courant.models import Event


def _row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        reminder_id=row["reminder_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        kind=row["kind"],
        value=row["value"],
    )


def insert_event(conn: sqlite3.Connection, e: Event) -> int:
    cursor = conn.execute(
        "INSERT INTO events (reminder_id, occurred_at, kind, value) VALUES (?, ?, ?, ?)",
        (e.reminder_id, e.occurred_at.isoformat(), e.kind, e.value),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def list_events_for_reminder(conn: sqlite3.Connection, reminder_id: int) -> list[Event]:
    rows = conn.execute(
        "SELECT * FROM events WHERE reminder_id = ? ORDER BY occurred_at",
        (reminder_id,),
    ).fetchall()
    return [_row_to_event(row) for row in rows]


def list_events_in_range(
    conn: sqlite3.Connection,
    start: datetime,
    end: datetime,
    reminder_id: int | None = None,
) -> list[Event]:
    """Events where start <= occurred_at < end. Optionally filtered by reminder."""
    if reminder_id is None:
        rows = conn.execute(
            "SELECT * FROM events WHERE occurred_at >= ? AND occurred_at < ? ORDER BY occurred_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events WHERE reminder_id = ? AND occurred_at >= ? AND occurred_at < ? "
            "ORDER BY occurred_at",
            (reminder_id, start.isoformat(), end.isoformat()),
        ).fetchall()
    return [_row_to_event(row) for row in rows]
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_repository.py -v`
Expected: all pass (13 total).

- [ ] **Step 5: Commit**

```bash
git add courant/repository.py tests/test_repository.py
git commit -m "feat(repo): Event insert and range queries"
```

---

## Task 6: `repository.py` — Settings k/v

**Files:**
- Modify: `courant/repository.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests (append)**

```python
from courant.repository import get_setting, set_setting


def test_set_and_get_setting(memory_db: sqlite3.Connection):
    migrate(memory_db)
    set_setting(memory_db, "snooze_minutes", "15")
    assert get_setting(memory_db, "snooze_minutes") == "15"


def test_get_setting_missing_returns_default(memory_db: sqlite3.Connection):
    migrate(memory_db)
    assert get_setting(memory_db, "nope", default="fallback") == "fallback"


def test_set_setting_upserts(memory_db: sqlite3.Connection):
    migrate(memory_db)
    set_setting(memory_db, "snooze_minutes", "10")
    set_setting(memory_db, "snooze_minutes", "20")
    assert get_setting(memory_db, "snooze_minutes") == "20"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_repository.py -v -k setting`
Expected: ImportError on setting functions.

- [ ] **Step 3: Implement (append to `courant/repository.py`)**

```python
def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_repository.py -v`
Expected: 16 total pass.

- [ ] **Step 5: Commit**

```bash
git add courant/repository.py tests/test_repository.py
git commit -m "feat(repo): settings get/set with upsert"
```

---

## Task 7: `repository.py` — Backup helper

**Files:**
- Modify: `courant/repository.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Write failing tests (append)**

```python
import time as time_module
from pathlib import Path

from courant.repository import backup_if_stale


def test_backup_creates_file_when_no_prior_backup(tmp_path: Path):
    db = tmp_path / "courant.db"
    conn = sqlite3.connect(db)
    migrate(conn)
    conn.close()

    created = backup_if_stale(db, max_age_hours=24, retain=7)
    assert created is not None
    assert created.exists()
    assert created.name.startswith("courant.db.backup-")


def test_backup_skips_if_recent(tmp_path: Path):
    db = tmp_path / "courant.db"
    conn = sqlite3.connect(db)
    migrate(conn)
    conn.close()

    first = backup_if_stale(db, max_age_hours=24, retain=7)
    assert first is not None
    second = backup_if_stale(db, max_age_hours=24, retain=7)
    assert second is None  # Not stale yet


def test_backup_prunes_old_backups(tmp_path: Path):
    db = tmp_path / "courant.db"
    conn = sqlite3.connect(db)
    migrate(conn)
    conn.close()

    # Manually create 10 old backups with distinct names
    for i in range(10):
        old = tmp_path / f"courant.db.backup-2026010{i}"
        old.write_bytes(b"fake")
        old_time = time_module.time() - (i + 1) * 86400
        import os
        os.utime(old, (old_time, old_time))

    backup_if_stale(db, max_age_hours=24, retain=7)
    remaining = sorted(tmp_path.glob("courant.db.backup-*"))
    assert len(remaining) == 7
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_repository.py -v -k backup`
Expected: ImportError on `backup_if_stale`.

- [ ] **Step 3: Implement (append to `courant/repository.py`)**

```python
import shutil
import time
from pathlib import Path


def backup_if_stale(db_path: Path, max_age_hours: int = 24, retain: int = 7) -> Path | None:
    """Create a timestamped backup if the most recent one is older than max_age_hours.

    Prunes backups beyond `retain` count (newest kept). Returns the new backup path,
    or None if no backup was created (too recent).
    """
    if not db_path.exists():
        return None

    parent = db_path.parent
    pattern = f"{db_path.name}.backup-*"
    existing = sorted(parent.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    if existing:
        most_recent_age_h = (time.time() - existing[0].stat().st_mtime) / 3600
        if most_recent_age_h < max_age_hours:
            return None

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = parent / f"{db_path.name}.backup-{timestamp}"
    shutil.copy2(db_path, backup_path)

    # Prune
    all_backups = sorted(parent.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in all_backups[retain:]:
        old.unlink()

    return backup_path
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_repository.py -v`
Expected: 19 total pass.

- [ ] **Step 5: Commit**

```bash
git add courant/repository.py tests/test_repository.py
git commit -m "feat(repo): daily backups with pruning"
```

---

## Task 8: `service.py` — ReminderService basic CRUD

**Files:**
- Create: `courant/service.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Write failing tests**

`tests/test_service.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_service.py -v`
Expected: ImportError on `courant.service`.

- [ ] **Step 3: Implement basic CRUD**

`courant/service.py`:
```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_service.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/service.py tests/test_service.py
git commit -m "feat(service): ReminderService basic CRUD"
```

---

## Task 9: `service.py` — `fire_reminder` + active window filter

**Files:**
- Modify: `courant/service.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write failing tests (append to `tests/test_service.py`)**

```python
from datetime import timedelta
from unittest.mock import MagicMock

from courant.repository import list_events_for_reminder


def test_is_in_active_window_inside(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(9, 0), time(18, 0))
    r.active_days = frozenset(Weekday)
    # Thursday 14:00
    now = datetime(2026, 5, 21, 14, 0)
    assert service.is_in_active_window(r, now) is True


def test_is_in_active_window_outside_hours(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(9, 0), time(18, 0))
    r.active_days = frozenset(Weekday)
    now = datetime(2026, 5, 21, 22, 0)
    assert service.is_in_active_window(r, now) is False


def test_is_in_active_window_wrong_day(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(0, 0), time(23, 59))
    r.active_days = frozenset({Weekday.MON})
    now = datetime(2026, 5, 21, 14, 0)  # Thursday
    assert service.is_in_active_window(r, now) is False


def test_fire_reminder_logs_event_and_calls_notifier(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    fake_notifier = MagicMock()
    service.fire_reminder(rid, notifier=fake_notifier, now=datetime(2026, 5, 21, 14, 0))

    events = list_events_for_reminder(service._conn, rid)
    assert len(events) == 1
    assert events[0].kind == "fired"
    fake_notifier.notify.assert_called_once()


def test_fire_reminder_skipped_when_outside_window(service: ReminderService):
    r = _new_reminder()
    r.active_hours = (time(9, 0), time(18, 0))
    r.active_days = frozenset(Weekday)
    rid = service.create_reminder(r)

    fake_notifier = MagicMock()
    service.fire_reminder(rid, notifier=fake_notifier, now=datetime(2026, 5, 21, 22, 0))

    assert list_events_for_reminder(service._conn, rid) == []
    fake_notifier.notify.assert_not_called()


def test_fire_reminder_skipped_when_paused(service: ReminderService):
    r = _new_reminder()
    r.paused_until = datetime(2026, 5, 21, 16, 0)
    rid = service.create_reminder(r)

    fake_notifier = MagicMock()
    service.fire_reminder(rid, notifier=fake_notifier, now=datetime(2026, 5, 21, 14, 0))

    assert list_events_for_reminder(service._conn, rid) == []
    fake_notifier.notify.assert_not_called()


def test_fire_reminder_no_op_for_missing_reminder(service: ReminderService):
    fake_notifier = MagicMock()
    # Should not raise
    service.fire_reminder(999, notifier=fake_notifier, now=datetime(2026, 5, 21, 14, 0))
    fake_notifier.notify.assert_not_called()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_service.py -v -k fire or window`
Expected: AttributeError on `is_in_active_window` / `fire_reminder`.

- [ ] **Step 3: Implement in `courant/service.py`**

Add the import and imports needed:
```python
from collections.abc import Callable
from courant.models import Event, Weekday
from courant.repository import insert_event
```

Add methods to `ReminderService`:
```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_service.py -v`
Expected: 11 passed (existing 4 + 7 new).

- [ ] **Step 5: Commit**

```bash
git add courant/service.py tests/test_service.py
git commit -m "feat(service): fire_reminder with active window + paused filter"
```

---

## Task 10: `service.py` — `handle_action`

**Files:**
- Modify: `courant/service.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write failing tests (append)**

```python
def test_handle_action_ack_logs_event_with_unit_amount(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.handle_action(rid, "ack", now=datetime(2026, 5, 21, 14, 0))
    events = list_events_for_reminder(service._conn, rid)
    assert len(events) == 1
    assert events[0].kind == "acked"
    assert events[0].value == 250  # unit_amount from _new_reminder


def test_handle_action_ack_no_value_when_untracked(service: ReminderService):
    r = _new_reminder()
    r.tracked = False
    r.unit_amount = None
    rid = service.create_reminder(r)
    service.handle_action(rid, "ack")
    events = list_events_for_reminder(service._conn, rid)
    assert events[0].kind == "acked"
    assert events[0].value is None


def test_handle_action_snooze_logs_event(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.handle_action(rid, "snooze")
    events = list_events_for_reminder(service._conn, rid)
    assert events[-1].kind == "snoozed"


def test_handle_action_dismissed(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    service.handle_action(rid, "dismissed")
    events = list_events_for_reminder(service._conn, rid)
    assert events[-1].kind == "dismissed"


def test_handle_action_unknown_is_silently_ignored(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    # Should not raise
    service.handle_action(rid, "bogus")
    assert list_events_for_reminder(service._conn, rid) == []


def test_handle_action_missing_reminder_silently_ignored(service: ReminderService):
    # Should not raise
    service.handle_action(9999, "ack")
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_service.py -v -k handle_action`
Expected: NotImplementedError raised.

- [ ] **Step 3: Replace `handle_action` stub in `service.py`**

```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_service.py -v`
Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/service.py tests/test_service.py
git commit -m "feat(service): handle_action for ack/snooze/dismiss"
```

---

## Task 11: `service.py` — `daily_progress`

**Files:**
- Modify: `courant/service.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write failing tests (append)**

```python
def test_daily_progress_counts_acked_events_today(service: ReminderService):
    r = _new_reminder()
    r.daily_goal = 8
    rid = service.create_reminder(r)
    today = datetime(2026, 5, 21, 12, 0)

    # Today: 3 acked
    for h in [9, 10, 11]:
        service.handle_action(rid, "ack", now=today.replace(hour=h))
    # Yesterday: 5 acked (should not count)
    yesterday = today.replace(day=20)
    for h in [9, 10, 11, 12, 13]:
        service.handle_action(rid, "ack", now=yesterday.replace(hour=h))

    progress = service.daily_progress(rid, now=today)
    assert progress.count == 3
    assert progress.goal == 8
    assert progress.percent == pytest.approx(37.5)


def test_daily_progress_ignores_non_ack_events(service: ReminderService):
    rid = service.create_reminder(_new_reminder())
    today = datetime(2026, 5, 21, 12, 0)
    service.handle_action(rid, "snooze", now=today)
    service.handle_action(rid, "dismissed", now=today)
    progress = service.daily_progress(rid, now=today)
    assert progress.count == 0


def test_daily_progress_for_untracked_reminder_has_no_goal(service: ReminderService):
    r = _new_reminder()
    r.tracked = False
    r.daily_goal = None
    rid = service.create_reminder(r)
    progress = service.daily_progress(rid, now=datetime(2026, 5, 21, 12, 0))
    assert progress.goal is None
    assert progress.percent is None
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_service.py -v -k daily_progress`
Expected: AttributeError on `daily_progress`.

- [ ] **Step 3: Implement in `service.py`**

Add a dataclass and method:
```python
from dataclasses import dataclass


@dataclass
class DailyProgress:
    reminder_id: int
    count: int
    goal: int | None
    percent: float | None
```

Add to `ReminderService`:
```python
    def daily_progress(self, reminder_id: int, now: datetime | None = None) -> DailyProgress:
        now = now or datetime.now()
        r = self.get_reminder(reminder_id)
        if r is None:
            return DailyProgress(reminder_id, 0, None, None)

        from courant.repository import list_events_in_range
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        events = list_events_in_range(self._conn, start, end, reminder_id=reminder_id)
        count = sum(1 for e in events if e.kind == "acked")
        goal = r.daily_goal if r.tracked else None
        percent = (count / goal * 100) if (goal and goal > 0) else None
        return DailyProgress(reminder_id, count, goal, percent)
```

Add `from datetime import timedelta` to the imports.

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_service.py -v`
Expected: 20 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/service.py tests/test_service.py
git commit -m "feat(service): daily_progress for tracked reminders"
```

---

## Task 12: `notifier.py` — Protocol + FakeNotifier

**Files:**
- Create: `courant/notifier.py`
- Test: `tests/test_notifier.py`

- [ ] **Step 1: Write failing tests**

`tests/test_notifier.py`:
```python
"""Tests for FakeNotifier (used as test double everywhere else)."""
from __future__ import annotations

from courant.notifier import FakeNotifier


def test_fake_notifier_records_calls():
    n = FakeNotifier()
    n.notify(
        title="Eau",
        body="Bois !",
        icon="💧",
        actions=[("ack", "Fait"), ("snooze", "Snooze")],
        on_action=lambda a: None,
    )
    assert len(n.calls) == 1
    call = n.calls[0]
    assert call.title == "Eau"
    assert call.body == "Bois !"
    assert call.icon == "💧"
    assert call.actions == [("ack", "Fait"), ("snooze", "Snooze")]


def test_fake_notifier_trigger_action_calls_back():
    n = FakeNotifier()
    received: list[str] = []
    n.notify(
        title="t", body="b", icon=None,
        actions=[("ack", "OK")],
        on_action=lambda a: received.append(a),
    )
    n.trigger_action(0, "ack")
    assert received == ["ack"]


def test_fake_notifier_trigger_invalid_call_index_raises():
    n = FakeNotifier()
    import pytest
    with pytest.raises(IndexError):
        n.trigger_action(0, "ack")
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_notifier.py -v`
Expected: ImportError on `courant.notifier`.

- [ ] **Step 3: Implement Protocol + FakeNotifier**

`courant/notifier.py`:
```python
"""Notification dispatch abstraction.

The Notifier protocol intentionally knows nothing about reminders, the DB,
or the scheduler. It just sends a (title, body, actions) tuple to whatever
backend is wired in. This lets tests use FakeNotifier without D-Bus, and
keeps future backends (web push, etc.) drop-in compatible.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


ActionId = str
ActionLabel = str
Action = tuple[ActionId, ActionLabel]
ActionCallback = Callable[[ActionId], None]


class Notifier(Protocol):
    def notify(
        self,
        title: str,
        body: str,
        icon: str | None,
        actions: list[Action],
        on_action: ActionCallback,
    ) -> None:
        ...


@dataclass
class _NotifyCall:
    title: str
    body: str
    icon: str | None
    actions: list[Action]
    on_action: ActionCallback


@dataclass
class FakeNotifier:
    """In-memory notifier for tests. Records calls and lets you trigger actions."""

    calls: list[_NotifyCall] = field(default_factory=list)

    def notify(
        self,
        title: str,
        body: str,
        icon: str | None,
        actions: list[Action],
        on_action: ActionCallback,
    ) -> None:
        self.calls.append(_NotifyCall(title, body, icon, actions, on_action))

    def trigger_action(self, call_index: int, action_id: ActionId) -> None:
        """Simulate the user clicking an action on a previously-sent notif."""
        self.calls[call_index].on_action(action_id)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_notifier.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/notifier.py tests/test_notifier.py
git commit -m "feat(notifier): Notifier protocol + FakeNotifier for tests"
```

---

## Task 13: `notifier.py` — DesktopNotifier (real impl)

**Files:**
- Modify: `courant/notifier.py`
- Modify: `tests/test_notifier.py`

- [ ] **Step 1: Write smoke test (skipped when D-Bus unavailable)**

Append to `tests/test_notifier.py`:
```python
import os
import pytest

from courant.notifier import DesktopNotifier


@pytest.mark.skipif(
    not os.environ.get("DBUS_SESSION_BUS_ADDRESS"),
    reason="No D-Bus session available (CI usually skips this)",
)
def test_desktop_notifier_smoke():
    """Sends a real notification — only runs when D-Bus is around."""
    n = DesktopNotifier(app_name="courant-test")
    n.notify(
        title="Courant test",
        body="If you see this, D-Bus integration works.",
        icon=None,
        actions=[],
        on_action=lambda a: None,
    )
    # Nothing to assert programmatically — visual check only
```

- [ ] **Step 2: Run tests, verify smoke test fails (no implementation)**

Run: `pytest tests/test_notifier.py -v`
Expected: `DesktopNotifier` import fails.

- [ ] **Step 3: Implement `DesktopNotifier` (append to `courant/notifier.py`)**

```python
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DesktopNotifier:
    """Notifier backed by the `desktop-notifier` library (D-Bus on Linux).

    Uses an event loop running in a background thread so callbacks fire
    without blocking the scheduler.
    """

    app_name: str = "Courant"
    _loop: asyncio.AbstractEventLoop | None = None
    _notifier: object | None = None  # desktop_notifier.DesktopNotifier

    def __post_init__(self) -> None:
        # Lazy-import so tests/CI without the lib still parse this file
        from desktop_notifier import DesktopNotifier as DN  # type: ignore[import-untyped]
        import threading

        self._loop = asyncio.new_event_loop()
        thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="courant-notif")
        thread.start()
        self._notifier = DN(app_name=self.app_name)

    def notify(
        self,
        title: str,
        body: str,
        icon: str | None,
        actions: list[Action],
        on_action: ActionCallback,
    ) -> None:
        from desktop_notifier import Button  # type: ignore[import-untyped]

        buttons = [
            Button(title=label, on_pressed=lambda aid=aid: on_action(aid))
            for aid, label in actions
        ]
        coro = self._notifier.send(  # type: ignore[union-attr]
            title=title,
            message=body,
            buttons=buttons,
        )
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _log_error(fut):
            exc = fut.exception()
            if exc:
                logger.warning("Notification failed: %s", exc)
        future.add_done_callback(_log_error)
```

- [ ] **Step 4: Run tests, verify they pass (skip on no D-Bus)**

Run: `pytest tests/test_notifier.py -v`
Expected: 3 passed, 1 skipped (smoke test).

If you want to manually verify the D-Bus integration:
```bash
python -c "from courant.notifier import DesktopNotifier; \
import time; n = DesktopNotifier(app_name='courant-test'); \
n.notify('hi', 'world', None, [('ok', 'OK')], lambda a: print(a)); time.sleep(3)"
```
Expected: see a notification pop up.

- [ ] **Step 5: Commit**

```bash
git add courant/notifier.py tests/test_notifier.py
git commit -m "feat(notifier): DesktopNotifier backend using desktop-notifier lib"
```

---

## Task 14: `scheduler.py` — `sync_jobs`

**Files:**
- Create: `courant/scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

`tests/test_scheduler.py`:
```python
"""Tests for ReminderScheduler. Uses APScheduler's BlockingScheduler in 'paused'
mode so we can introspect jobs without them actually running."""
from __future__ import annotations

import sqlite3
from datetime import datetime, time
from unittest.mock import MagicMock

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from courant.models import Reminder, Weekday
from courant.repository import migrate
from courant.scheduler import ReminderScheduler
from courant.service import ReminderService


@pytest.fixture
def stopped_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler()
    yield sched
    if sched.running:
        sched.shutdown(wait=False)


def _new_reminder(name: str = "Eau", interval: int = 30) -> Reminder:
    return Reminder(
        id=None, name=name, message="m", icon=None,
        interval_minutes=interval,
        active_hours=(time(0, 0), time(23, 59)),
        active_days=frozenset(Weekday),
        enabled=True, tracked=False,
        unit_label=None, unit_amount=None, daily_goal=None,
        created_at=datetime(2026, 5, 21, 10, 0), paused_until=None,
    )


def test_sync_jobs_adds_one_job_per_active_reminder(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    migrate(memory_db)
    service = ReminderService(memory_db)
    service.create_reminder(_new_reminder("A", interval=30))
    service.create_reminder(_new_reminder("B", interval=45))

    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())
    rs.sync_jobs()

    jobs = stopped_scheduler.get_jobs()
    assert len(jobs) == 2
    assert {j.id for j in jobs} == {"reminder-1", "reminder-2"}


def test_sync_jobs_replaces_existing_jobs_on_update(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_new_reminder("A", interval=30))

    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())
    rs.sync_jobs()
    initial_job = stopped_scheduler.get_job("reminder-1")
    assert initial_job is not None

    r = service.get_reminder(rid)
    assert r is not None
    r.interval_minutes = 60
    service.update_reminder(r)
    rs.sync_jobs()

    updated_job = stopped_scheduler.get_job("reminder-1")
    assert updated_job is not None
    assert updated_job.trigger.interval.total_seconds() == 60 * 60


def test_sync_jobs_removes_jobs_for_deleted_reminders(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_new_reminder("A"))
    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())
    rs.sync_jobs()
    assert stopped_scheduler.get_job(f"reminder-{rid}") is not None

    service.delete_reminder(rid)
    rs.sync_jobs()
    assert stopped_scheduler.get_job(f"reminder-{rid}") is None


def test_sync_jobs_removes_jobs_for_disabled_reminders(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_new_reminder("A"))
    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())
    rs.sync_jobs()

    r = service.get_reminder(rid)
    assert r is not None
    r.enabled = False
    service.update_reminder(r)
    rs.sync_jobs()
    assert stopped_scheduler.get_job(f"reminder-{rid}") is None
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_scheduler.py -v`
Expected: ImportError on `courant.scheduler`.

- [ ] **Step 3: Implement `courant/scheduler.py`**

```python
"""Reminder scheduling via APScheduler.

Each active reminder gets one IntervalTrigger job with id `reminder-{id}`.
On every sync_jobs(), we add/update active reminders and remove stale ones.
"""
from __future__ import annotations

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.interval import IntervalTrigger

from courant.notifier import Notifier
from courant.service import ReminderService


_JOB_ID_PREFIX = "reminder-"


def _job_id(reminder_id: int) -> str:
    return f"{_JOB_ID_PREFIX}{reminder_id}"


class ReminderScheduler:
    def __init__(
        self,
        scheduler: BaseScheduler,
        service: ReminderService,
        notifier: Notifier,
    ) -> None:
        self._scheduler = scheduler
        self._service = service
        self._notifier = notifier

    def sync_jobs(self) -> None:
        """Reconcile scheduler state with service.list_active_reminders().

        Idempotent: call after any reminder CRUD operation.
        """
        active = self._service.list_active_reminders()
        active_ids = {r.id for r in active if r.id is not None}

        # Remove jobs for reminders that disappeared or got disabled
        for job in self._scheduler.get_jobs():
            if not job.id.startswith(_JOB_ID_PREFIX):
                continue  # not ours (e.g. snooze jobs from task 15)
            jid = int(job.id[len(_JOB_ID_PREFIX):])
            if jid not in active_ids:
                self._scheduler.remove_job(job.id)

        # Add or update jobs for active reminders
        for r in active:
            assert r.id is not None
            self._scheduler.add_job(
                func=self._fire,
                args=[r.id],
                trigger=IntervalTrigger(minutes=r.interval_minutes),
                id=_job_id(r.id),
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )

    def _fire(self, reminder_id: int) -> None:
        self._service.fire_reminder(reminder_id, notifier=self._notifier)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/scheduler.py tests/test_scheduler.py
git commit -m "feat(scheduler): sync_jobs reconciles APScheduler with reminders"
```

---

## Task 15: `scheduler.py` — `schedule_once` for snooze

**Files:**
- Modify: `courant/scheduler.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests (append)**

```python
def test_schedule_once_creates_single_run_job(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    from apscheduler.triggers.date import DateTrigger

    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_new_reminder("A"))
    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())

    fire_time = datetime(2026, 5, 21, 14, 15)
    rs.schedule_once(rid, fire_time)

    job = stopped_scheduler.get_job(f"snooze-{rid}-{fire_time.isoformat()}")
    assert job is not None
    assert isinstance(job.trigger, DateTrigger)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_scheduler.py -v -k schedule_once`
Expected: AttributeError on `schedule_once`.

- [ ] **Step 3: Implement (add to `ReminderScheduler` in `scheduler.py`)**

Add import:
```python
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
```

Add method:
```python
    def schedule_once(self, reminder_id: int, fire_at: datetime) -> None:
        """Schedule a one-shot fire (used for snooze). Job ID is unique per fire time."""
        self._scheduler.add_job(
            func=self._fire,
            args=[reminder_id],
            trigger=DateTrigger(run_date=fire_at),
            id=f"snooze-{reminder_id}-{fire_at.isoformat()}",
            replace_existing=True,
        )
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/scheduler.py tests/test_scheduler.py
git commit -m "feat(scheduler): schedule_once for snooze jobs"
```

---

## Task 16: `cli.py` — argparse skeleton + `version`

**Files:**
- Create: `courant/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cli.py`:
```python
"""Tests for the courant CLI."""
from __future__ import annotations

import pytest

from courant.cli import main


def test_version_command(capsys: pytest.CaptureFixture[str]):
    exit_code = main(["version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "courant" in out.lower()
    # Expect a SemVer-ish string
    assert any(ch.isdigit() for ch in out)


def test_no_args_prints_help_and_exits_nonzero(capsys: pytest.CaptureFixture[str]):
    exit_code = main([])
    assert exit_code != 0
    err_or_out = capsys.readouterr()
    combined = err_or_out.out + err_or_out.err
    assert "usage" in combined.lower()


def test_unknown_command_errors(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as excinfo:
        main(["does-not-exist"])
    assert excinfo.value.code != 0
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: ImportError on `courant.cli`.

- [ ] **Step 3: Implement `courant/cli.py`**

```python
"""Command-line entry point for Courant.

`main(argv=None)` is the testable function. The console_script `courant`
calls main() with sys.argv[1:].
"""
from __future__ import annotations

import argparse
import sys

from courant import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="courant",
        description="Un rappel cozy pour les devs : eau, yeux, étirements.",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("version", help="Print version and exit")
    subparsers.add_parser("start", help="Start the daemon (foreground)")
    subparsers.add_parser("stop", help="Stop the systemd-managed daemon")
    subparsers.add_parser("status", help="Show daemon status and URL")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 2

    if args.command == "version":
        print(f"courant {__version__}")
        return 0

    # start/stop/status implemented in subsequent tasks
    print(f"command '{args.command}' not yet implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add courant/cli.py tests/test_cli.py
git commit -m "feat(cli): argparse skeleton + version command"
```

---

## Task 17: `cli.py` — `start` command (wires everything together)

**Files:**
- Modify: `courant/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_cli.py`:
```python
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


def test_start_creates_db_and_seeds_default_reminders(
    isolated_paths: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    """Spawn `python -m courant.cli start` in a subprocess, give it 2s, kill it,
    then verify the DB was created and seeded."""
    # The default_reminders seed lands in Task 20. For now, just verify the DB
    # is created and migrated.
    env = {
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "PATH": __import__("os").environ.get("PATH", ""),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "courant.cli", "start"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(2)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=5)

    db = tmp_path / "data" / "courant" / "courant.db"
    assert db.exists()
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"reminders", "events", "settings"}.issubset(tables)
```

Also add a module-level entry so `python -m courant.cli` works:

Create `courant/__main__.py`:
```python
from courant.cli import main
import sys
sys.exit(main())
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_cli.py::test_start_creates_db_and_seeds_default_reminders -v`
Expected: AssertionError (db not created) or the subprocess crashes.

- [ ] **Step 3: Implement `start` in `courant/cli.py`**

Add at module level:
```python
import logging
import os
import signal
import time as time_module

from apscheduler.schedulers.background import BackgroundScheduler

from courant.notifier import DesktopNotifier, FakeNotifier, Notifier
from courant.paths import db_path, ensure_dirs, log_path
from courant.repository import backup_if_stale, connect, migrate
from courant.scheduler import ReminderScheduler
from courant.service import ReminderService

logger = logging.getLogger("courant")


def _setup_logging() -> None:
    ensure_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path()),
        ],
    )


def _build_notifier() -> Notifier:
    """Try DesktopNotifier; fall back to FakeNotifier on failure (logged)."""
    try:
        return DesktopNotifier(app_name="Courant")
    except Exception as exc:  # noqa: BLE001 — fallback is intentional
        logger.warning("Falling back to FakeNotifier (no notifications): %s", exc)
        return FakeNotifier()


def _run_daemon() -> int:
    _setup_logging()
    ensure_dirs()
    backup_if_stale(db_path())
    conn = connect(str(db_path()))
    migrate(conn)

    service = ReminderService(conn)
    notifier = _build_notifier()
    apsched = BackgroundScheduler()
    rs = ReminderScheduler(scheduler=apsched, service=service, notifier=notifier)
    rs.sync_jobs()
    rs.start()

    logger.info("Courant daemon started (PID %d)", os.getpid())

    stop_requested = False

    def _on_signal(signum, _frame):
        nonlocal stop_requested
        logger.info("Received signal %d, shutting down", signum)
        stop_requested = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    try:
        while not stop_requested:
            time_module.sleep(0.5)
    finally:
        rs.shutdown()
        conn.close()
    return 0
```

Modify the `main()` body to dispatch `start`:
```python
    if args.command == "start":
        return _run_daemon()
```

- [ ] **Step 4: Run test, verify it passes**

Run: `pytest tests/test_cli.py::test_start_creates_db_and_seeds_default_reminders -v -s`
Expected: passes (db exists, tables present).

If on a CI box without D-Bus, the `_build_notifier` falls back to `FakeNotifier` — that's intended.

- [ ] **Step 5: Commit**

```bash
git add courant/cli.py courant/__main__.py tests/test_cli.py
git commit -m "feat(cli): start command wires service/scheduler/notifier"
```

---

## Task 18: `cli.py` — `status` command

**Files:**
- Modify: `courant/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_cli.py`:
```python
def test_status_when_no_db(isolated_paths: Path, capsys: pytest.CaptureFixture[str]):
    exit_code = main(["status"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "not initialized" in out.lower() or "no database" in out.lower()


def test_status_with_db_shows_reminder_count(
    isolated_paths: Path, capsys: pytest.CaptureFixture[str],
):
    # Set up a DB with one reminder
    from courant.paths import db_path, ensure_dirs
    from courant.repository import connect, insert_reminder, migrate
    from datetime import datetime, time
    from courant.models import Reminder, Weekday

    ensure_dirs()
    conn = connect(str(db_path()))
    migrate(conn)
    insert_reminder(conn, Reminder(
        id=None, name="Eau", message="m", icon=None, interval_minutes=45,
        active_hours=(time(9, 0), time(18, 0)),
        active_days=frozenset(Weekday), enabled=True, tracked=False,
        unit_label=None, unit_amount=None, daily_goal=None,
        created_at=datetime.now(), paused_until=None,
    ))
    conn.close()

    exit_code = main(["status"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "1" in out
    assert "eau" in out.lower() or "reminder" in out.lower()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_cli.py::test_status_when_no_db -v`
Expected: fails because `status` returns 1 (not implemented).

- [ ] **Step 3: Implement `status` in `cli.py`**

Add a function:
```python
def _run_status() -> int:
    db = db_path()
    if not db.exists():
        print("Courant not initialized (no database found).")
        print(f"Expected at: {db}")
        return 0

    conn = connect(str(db))
    try:
        rows = conn.execute("SELECT id, name, enabled FROM reminders ORDER BY id").fetchall()
    finally:
        conn.close()

    print(f"Courant — database at {db}")
    print(f"Reminders configured: {len(rows)}")
    for row in rows:
        status = "enabled" if row["enabled"] else "disabled"
        print(f"  [{row['id']:>2}] {row['name']} ({status})")
    return 0
```

Add dispatch:
```python
    if args.command == "status":
        return _run_status()
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add courant/cli.py tests/test_cli.py
git commit -m "feat(cli): status command shows DB state and reminders"
```

---

## Task 19: `cli.py` — `stop` command

**Files:**
- Modify: `courant/cli.py`
- Modify: `tests/test_cli.py`

The `stop` command stops the systemd-managed instance. Without systemd it's a no-op with a helpful message. The systemd `install` command lands in Phase 4 — for now `stop` just tells the user how to stop the foreground daemon.

- [ ] **Step 1: Write failing test**

Append to `tests/test_cli.py`:
```python
def test_stop_when_no_systemd_prints_instructions(
    isolated_paths: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
):
    # Force the "no systemd" branch by pointing PATH to an empty dir
    empty_bin = isolated_paths / "empty_bin"
    empty_bin.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PATH", str(empty_bin))

    exit_code = main(["stop"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "systemd" in out.lower() or "ctrl" in out.lower()
```

- [ ] **Step 2: Run test, verify it fails**

Run: `pytest tests/test_cli.py::test_stop_when_no_systemd_prints_instructions -v`
Expected: fails (stop returns 1, not 0).

- [ ] **Step 3: Implement `stop`**

```python
import shutil
import subprocess


def _run_stop() -> int:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        print("systemctl not found. If you ran `courant start` in foreground, stop it with Ctrl+C.")
        return 0

    result = subprocess.run(
        [systemctl, "--user", "stop", "courant.service"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("Courant service stopped.")
        return 0
    # Service not installed yet — common case in Phase 1
    print("No running courant.service found via systemd.")
    print("If you ran `courant start` in foreground, stop it with Ctrl+C.")
    return 0
```

Add dispatch:
```python
    if args.command == "stop":
        return _run_stop()
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add courant/cli.py tests/test_cli.py
git commit -m "feat(cli): stop command (foreground-friendly placeholder)"
```

---

## Task 20: `default_reminders.json` seed + first-launch logic

**Files:**
- Create: `courant/data/default_reminders.json`
- Modify: `courant/service.py`
- Modify: `courant/cli.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write failing tests (append to `tests/test_service.py`)**

```python
def test_seed_default_reminders_on_empty_db(service: ReminderService):
    assert service.list_reminders() == []
    service.seed_defaults_if_empty()
    reminders = service.list_reminders()
    assert len(reminders) >= 2
    names = [r.name for r in reminders]
    assert "Boire de l'eau" in names


def test_seed_default_reminders_is_noop_when_not_empty(service: ReminderService):
    service.create_reminder(_new_reminder("Existing"))
    service.seed_defaults_if_empty()
    reminders = service.list_reminders()
    assert len(reminders) == 1
    assert reminders[0].name == "Existing"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `pytest tests/test_service.py -v -k seed`
Expected: AttributeError on `seed_defaults_if_empty`.

- [ ] **Step 3: Create the seed file**

`courant/data/default_reminders.json`:
```json
[
  {
    "name": "Boire de l'eau",
    "message": "Hydrate-toi 💧",
    "icon": "💧",
    "interval_minutes": 45,
    "active_hours_start": "09:00",
    "active_hours_end": "18:00",
    "active_days": "mon,tue,wed,thu,fri",
    "tracked": true,
    "unit_label": "verre",
    "unit_amount": 250,
    "daily_goal": 8
  },
  {
    "name": "Pause yeux (20-20-20)",
    "message": "Regarde quelque chose à 6 mètres pendant 20 secondes 👀",
    "icon": "👀",
    "interval_minutes": 20,
    "active_hours_start": "09:00",
    "active_hours_end": "18:00",
    "active_days": "mon,tue,wed,thu,fri",
    "tracked": false
  },
  {
    "name": "Étirements",
    "message": "Lève-toi, étire-toi 🦵",
    "icon": "🦵",
    "interval_minutes": 90,
    "active_hours_start": "09:00",
    "active_hours_end": "18:00",
    "active_days": "mon,tue,wed,thu,fri",
    "tracked": false
  }
]
```

- [ ] **Step 4: Implement `seed_defaults_if_empty` in `service.py`**

Add imports:
```python
import json
from importlib import resources
```

Add method:
```python
    def seed_defaults_if_empty(self) -> int:
        """If no reminders exist, populate from default_reminders.json. Returns count seeded."""
        if self.list_reminders():
            return 0
        with resources.files("courant.data").joinpath("default_reminders.json").open("r") as f:
            entries = json.load(f)

        count = 0
        for entry in entries:
            r = Reminder(
                id=None,
                name=entry["name"],
                message=entry["message"],
                icon=entry.get("icon"),
                interval_minutes=entry["interval_minutes"],
                active_hours=(
                    parse_time(entry.get("active_hours_start", "09:00")),
                    parse_time(entry.get("active_hours_end", "18:00")),
                ),
                active_days=parse_active_days(entry.get("active_days", "mon,tue,wed,thu,fri")),
                enabled=True,
                tracked=entry.get("tracked", False),
                unit_label=entry.get("unit_label"),
                unit_amount=entry.get("unit_amount"),
                daily_goal=entry.get("daily_goal"),
                created_at=datetime.now(),
                paused_until=None,
            )
            self.create_reminder(r)
            count += 1
        return count
```

Add imports:
```python
from courant.models import Reminder, parse_active_days, parse_time
```

(Reminder already imported, just add parse_* helpers.)

- [ ] **Step 5: Make `courant/data/` a Python package**

`importlib.resources.files("courant.data")` requires a real package, so create:

`courant/data/__init__.py` — empty file.

Hatchling's default wheel build includes non-Python files in packages, so the JSON ships in the wheel automatically.

- [ ] **Step 6: Wire into `cli.py` `_run_daemon`**

In `cli.py`, after `service = ReminderService(conn)`, add:
```python
    seeded = service.seed_defaults_if_empty()
    if seeded:
        logger.info("Seeded %d default reminders on first launch", seeded)
```

- [ ] **Step 7: Run tests, verify they pass**

Run: `pytest -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add courant/data/ courant/service.py courant/cli.py tests/test_service.py
git commit -m "feat: seed default reminders on first launch"
```

---

## Task 21: End-to-end smoke verification + lint/typecheck

**Files:**
- Manual verification only, plus tooling runs.

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`
Expected: all tests pass (no failures, smoke test on D-Bus may skip).

- [ ] **Step 2: Run ruff**

Run: `ruff check courant tests`
Expected: no errors. Fix any reported with `ruff check --fix` and review the diff.

- [ ] **Step 3: Run mypy**

Run: `mypy courant`
Expected: no errors. Fix any reported (typically: missing annotations or `Any` returns from untyped libs — add `# type: ignore[reason]` only with a justified comment).

- [ ] **Step 4: Manual end-to-end smoke**

In one terminal:
```bash
courant start
```
Expected logs:
- "Courant daemon started (PID …)"
- "Seeded 3 default reminders on first launch"

In another terminal:
```bash
courant status
```
Expected:
- "Courant — database at /home/…/.local/share/courant/courant.db"
- "Reminders configured: 3"
- Lists "Boire de l'eau", "Pause yeux", "Étirements"

To force a notification quickly without waiting 20+ minutes, temporarily edit a reminder to `interval_minutes=1` via:
```bash
sqlite3 ~/.local/share/courant/courant.db \
  "UPDATE reminders SET interval_minutes=1 WHERE name LIKE 'Pause yeux%'"
```
Then restart `courant start`. Within ~1 min, expect a desktop notification with title "Pause yeux (20-20-20)" and a "Snooze 10min" button.

Click the notification body / action and verify (in another terminal):
```bash
sqlite3 ~/.local/share/courant/courant.db "SELECT * FROM events ORDER BY id DESC LIMIT 5"
```
Expected: an entry with `kind='fired'`, and if you clicked the action, another with `kind='acked'` or `kind='snoozed'`.

Stop the daemon with Ctrl+C in the foreground terminal. Verify clean shutdown in logs:
- "Received signal 2, shutting down"

- [ ] **Step 5: Document Phase 1 completion in README**

Update `README.md` to add a "Status" line and basic usage:

```markdown
# Courant

> Un rappel cozy pour les devs : eau, yeux, étirements.

Linux desktop app that sends customizable notifications to remind you to drink water, rest your eyes, stretch — with a cozy lo-fi web interface (coming in Phase 2).

**Status:**
- ✅ Phase 1 (Core CLI + notifications) — done
- ⏳ Phase 2 (Web UI) — next
- ⏳ Phase 3 (Cozy aesthetic, scenes)
- ⏳ Phase 4 (Polish, systemd, PyPI)

## Quick start (dev)

    git clone https://github.com/<user>/courant
    cd courant
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"

    courant start                    # foreground daemon
    courant status                   # in another terminal: see reminders
    # Ctrl+C in the daemon terminal to stop

On first launch, three default reminders are seeded: water (45 min, tracked, 8 verres/day), eye breaks (20 min), stretching (90 min).

## Tests

    pytest -v

## License

MIT
```

- [ ] **Step 6: Commit and tag Phase 1**

```bash
git add README.md
git commit -m "docs: mark Phase 1 complete and update quick start"
git tag -a phase-1-complete -m "Phase 1: Core CLI + notifications working end-to-end"
```

---

## Phase 1 Done ✓

At this point the daemon:
- Stores reminders, events, and settings in SQLite under XDG paths
- Sends real desktop notifications on schedule via D-Bus
- Handles ack/snooze/dismiss action callbacks
- Backups DB daily, retains 7 days
- Has 30+ unit tests, lint-clean, type-clean

**Next phase:** Write `2026-XX-XX-courant-phase-2-web-ui.md` plan for FastAPI + Jinja templates + HTMX (no aesthetic styling yet — that's Phase 3).
