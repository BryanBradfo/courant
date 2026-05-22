"""Tests for the FastAPI web UI."""
from __future__ import annotations

import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from courant.repository import migrate
from courant.service import ReminderService
from courant.web import create_app


@pytest.fixture
def app_with_empty_db(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    return create_app(service)


async def test_health_endpoint(app_with_empty_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_empty_db), base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_dashboard_renders(app_with_empty_db):
    async with AsyncClient(transport=ASGITransport(app=app_with_empty_db), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "Courant" in resp.text
    assert "text/html" in resp.headers["content-type"]


from datetime import datetime, time
from courant.models import Reminder, Weekday


def _make_reminder(name: str, tracked: bool = True) -> Reminder:
    return Reminder(
        id=None, name=name, message=f"Time to {name.lower()}",
        icon="💧" if "water" in name.lower() else None,
        interval_minutes=45,
        active_hours=(time(0, 0), time(23, 59)),
        active_days=frozenset(Weekday),
        enabled=True, tracked=tracked,
        unit_label="glass" if tracked else None,
        unit_amount=250 if tracked else None,
        daily_goal=8 if tracked else None,
        created_at=datetime(2026, 5, 22, 10, 0), paused_until=None,
    )


async def test_dashboard_shows_reminder_names(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    service.create_reminder(_make_reminder("Water"))
    service.create_reminder(_make_reminder("Stretch", tracked=False))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "Water" in resp.text
    assert "Stretch" in resp.text


async def test_dashboard_shows_progress_for_tracked(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    service.handle_action(rid, "ack")
    service.handle_action(rid, "ack")
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert "2 / 8" in resp.text or "2/8" in resp.text  # progress label


async def test_post_event_ack_increments_progress(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/events", data={"reminder_id": rid, "kind": "ack"})
    assert resp.status_code == 200
    # The response is the updated card HTML (HTMX swap target)
    assert "1 / 8" in resp.text or "1/8" in resp.text


async def test_post_event_unknown_kind_400(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/events", data={"reminder_id": rid, "kind": "bogus"})
    assert resp.status_code == 400


async def test_reminders_page_lists_all(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    service.create_reminder(_make_reminder("Water"))
    service.create_reminder(_make_reminder("Stretch", tracked=False))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/reminders")
    assert resp.status_code == 200
    assert "Water" in resp.text
    assert "Stretch" in resp.text
    assert "Add reminder" in resp.text or "New reminder" in resp.text


async def test_reminders_page_empty_state(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/reminders")
    assert resp.status_code == 200
    assert "No reminders" in resp.text or "no reminders" in resp.text.lower()


# --- Task 6: New reminder form + POST /reminders ---

async def test_new_reminder_form_renders(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/reminders/new")
    assert resp.status_code == 200
    assert "<form" in resp.text
    assert 'name="name"' in resp.text
    assert 'name="message"' in resp.text
    assert 'name="interval_minutes"' in resp.text


async def test_post_creates_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/reminders", data={
            "name": "Tea",
            "message": "Tea time !",
            "icon": "🍵",
            "interval_minutes": "60",
            "active_hours_start": "09:00",
            "active_hours_end": "18:00",
            "active_days": "mon,tue,wed,thu,fri",
            "tracked": "on",
            "unit_label": "cup",
            "unit_amount": "200",
            "daily_goal": "4",
        }, follow_redirects=False)

    # POST should redirect to /reminders after creation
    assert resp.status_code in (302, 303)
    # Verify it landed in the service
    reminders = service.list_reminders()
    assert any(r.name == "Tea" for r in reminders)


async def test_post_missing_required_field_400(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/reminders", data={"message": "no name"})
    assert resp.status_code in (400, 422)


# --- Task 7: Edit reminder form + POST update ---

async def test_edit_form_prefills(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/reminders/{rid}/edit")
    assert resp.status_code == 200
    assert 'value="Water"' in resp.text


async def test_post_updates_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/reminders/{rid}", data={
            "name": "Water (updated)",
            "message": "Drink !",
            "interval_minutes": "30",
            "active_hours_start": "10:00",
            "active_hours_end": "17:00",
            "active_days": "mon,tue,wed",
        }, follow_redirects=False)
    assert resp.status_code in (302, 303)
    updated = service.get_reminder(rid)
    assert updated is not None
    assert updated.name == "Water (updated)"
    assert updated.interval_minutes == 30


async def test_edit_missing_reminder_404(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/reminders/9999/edit")
    assert resp.status_code == 404


# --- Task 8: Delete reminder ---

async def test_delete_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/reminders/{rid}/delete", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert service.get_reminder(rid) is None


# --- Task 9: Toggle enable/disable ---

async def test_toggle_disables_then_enables(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/reminders/{rid}/toggle")
        assert resp.status_code == 200
        # Response is the new row HTML
        assert "disabled" in resp.text.lower()

        resp = await client.post(f"/reminders/{rid}/toggle")
        assert "disabled" not in resp.text.lower() or "enabled" in resp.text.lower()

    # Final state: enabled again
    r = service.get_reminder(rid)
    assert r is not None and r.enabled is True


# --- Task 10: /stats page ---

async def test_stats_page_shows_per_reminder_today(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    service.handle_action(rid, "ack")
    service.handle_action(rid, "ack")
    service.handle_action(rid, "ack")
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/stats")
    assert resp.status_code == 200
    assert "Water" in resp.text
    assert "3" in resp.text  # today's count


# --- Task 11: /settings page ---

async def test_settings_page_shows_snooze_value(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/settings")
    assert resp.status_code == 200
    assert "Snooze" in resp.text
    assert "10" in resp.text  # default snooze minutes


async def test_settings_post_updates_value(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/settings", data={"snooze_minutes": "15"}, follow_redirects=False)
    assert resp.status_code in (302, 303)
    from courant.repository import get_setting
    assert get_setting(memory_db, "snooze_minutes") == "15"
