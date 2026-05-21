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
