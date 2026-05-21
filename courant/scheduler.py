"""Reminder scheduling via APScheduler.

Each active reminder gets one IntervalTrigger job with id `reminder-{id}`.
On every sync_jobs(), we add/update active reminders and remove stale ones.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.date import DateTrigger
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
            jid = _job_id(r.id)
            existing = self._scheduler.get_job(jid)
            new_interval = timedelta(minutes=r.interval_minutes)
            if existing is not None:
                existing_interval = getattr(existing.trigger, "interval", None)
                if existing_interval == new_interval:
                    continue  # unchanged, no need to reset next-run-time
                self._scheduler.remove_job(jid)
            self._scheduler.add_job(
                func=self._fire,
                args=[r.id],
                trigger=IntervalTrigger(minutes=r.interval_minutes),
                id=jid,
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )

    def schedule_once(self, reminder_id: int, fire_at: datetime) -> None:
        """Schedule a one-shot snooze job for a reminder.

        Job id: ``snooze-{reminder_id}-{fire_at.isoformat()}``.
        Uses DateTrigger so it fires exactly once at *fire_at*.
        """
        job_id = f"snooze-{reminder_id}-{fire_at.isoformat()}"
        self._scheduler.add_job(
            func=self._fire,
            args=[reminder_id],
            trigger=DateTrigger(run_date=fire_at),
            id=job_id,
            replace_existing=True,
        )

    def _fire(self, reminder_id: int) -> None:
        self._service.fire_reminder(reminder_id, notifier=self._notifier)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
