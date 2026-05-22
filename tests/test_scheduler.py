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


def test_schedule_once_creates_single_run_job(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_new_reminder("A"))

    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())
    fire_time = datetime(2026, 5, 21, 15, 30, 0)
    rs.schedule_once(rid, fire_time)

    expected_id = f"snooze-{rid}-{fire_time.isoformat()}"
    job = stopped_scheduler.get_job(expected_id)
    assert job is not None
    from apscheduler.triggers.date import DateTrigger
    assert isinstance(job.trigger, DateTrigger)


def test_sync_jobs_preserves_next_run_when_unchanged(
    memory_db: sqlite3.Connection, stopped_scheduler: BackgroundScheduler,
):
    """If a reminder's interval is unchanged, sync_jobs should NOT recreate the job."""
    migrate(memory_db)
    service = ReminderService(memory_db)
    service.create_reminder(_new_reminder("A", interval=30))

    rs = ReminderScheduler(scheduler=stopped_scheduler, service=service, notifier=MagicMock())
    rs.sync_jobs()
    first_job = stopped_scheduler.get_job("reminder-1")
    assert first_job is not None
    # Capture trigger identity — should be the same object after a no-op sync
    first_trigger_id = id(first_job.trigger)

    rs.sync_jobs()  # No reminder changes; job should not be recreated
    second_job = stopped_scheduler.get_job("reminder-1")
    assert second_job is not None
    assert id(second_job.trigger) == first_trigger_id  # same trigger object => not recreated


import threading  # noqa: E402
import time as time_module  # noqa: E402

from courant.notifier import FakeNotifier  # noqa: E402
from courant.repository import list_events_for_reminder  # noqa: E402


def test_scheduler_fires_from_worker_thread(
    memory_db: sqlite3.Connection,
):
    """Regression: APScheduler runs jobs in worker threads, but service/repository
    use the connection created in the main thread. Must not raise
    sqlite3.ProgrammingError about cross-thread usage.
    """
    # Use a real file-based DB rather than :memory: because :memory: connections
    # cannot be shared even with check_same_thread=False (each connection sees
    # its own :memory: DB). This test verifies the cross-thread fix in connect().
    import tempfile
    from pathlib import Path
    from courant.repository import connect

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = connect(str(db_path))
        migrate(conn)

        service = ReminderService(conn)
        rid = service.create_reminder(_new_reminder("Threading test", interval=1))

        notifier = FakeNotifier()
        sched = BackgroundScheduler()
        rs = ReminderScheduler(scheduler=sched, service=service, notifier=notifier)
        rs.sync_jobs()

        # Override the interval to fire almost immediately (300ms from now)
        from datetime import datetime, timedelta
        rs.schedule_once(rid, datetime.now() + timedelta(milliseconds=300))

        try:
            rs.start()
            # Give the scheduler up to 3 seconds to fire the one-shot job
            for _ in range(30):
                if notifier.calls:
                    break
                time_module.sleep(0.1)
        finally:
            rs.shutdown()
            conn.close()

        assert len(notifier.calls) >= 1, (
            "Scheduler worker thread should fire notification without "
            "sqlite3 cross-thread error"
        )
        # Verify the event was logged (proves the worker thread successfully
        # wrote to the DB through the cross-thread connection)
        events = list_events_for_reminder(connect(str(db_path)), rid)
        assert any(e.kind == "fired" for e in events)
