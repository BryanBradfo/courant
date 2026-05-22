"""FastAPI web UI for Courant.

create_app(service) returns a FastAPI instance configured with all routes
and Jinja templates. The caller (cli.py) injects the shared ReminderService.
This keeps web.py testable in isolation (just pass a service backed by an
in-memory DB).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from courant.models import Reminder, format_active_days, parse_active_days, parse_time
from courant.repository import get_setting, set_setting
from courant.service import ReminderService

_PACKAGE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"

AVAILABLE_SCENES = ("ocean-depth", "rainy-window", "sunset-beach", "forest-stream", "calm-night")


def create_app(service: ReminderService) -> FastAPI:
    app = FastAPI(
        title="Courant",
        description="A cozy reminder for developers.",
        # Disable the default /docs and /redoc — internal-only API.
        docs_url=None,
        redoc_url=None,
    )

    def _base_context() -> dict[str, str]:
        raw = get_setting(service._conn, "current_scene", default="ocean-depth")
        current_scene: str = raw or "ocean-depth"
        return {"current_scene": current_scene}

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        progresses = {r.id: service.daily_progress(r.id) for r in reminders if r.id is not None}
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {**_base_context(), "reminders": reminders, "progresses": progresses},
        )

    @app.post("/api/events", response_class=HTMLResponse)
    async def post_event(
        request: Request,
        reminder_id: int = Form(...),
        kind: str = Form(...),
    ) -> HTMLResponse:
        if kind not in ("ack", "snooze", "dismissed"):
            raise HTTPException(status_code=400, detail=f"Unknown action: {kind}")
        service.handle_action(reminder_id, kind)
        r = service.get_reminder(reminder_id)
        if r is None:
            raise HTTPException(status_code=404, detail="Reminder not found")
        progress = service.daily_progress(reminder_id)
        return templates.TemplateResponse(
            request,
            "partials/reminder_card.html",
            {**_base_context(), "r": r, "progress": progress},
        )

    @app.get("/reminders", response_class=HTMLResponse)
    async def reminders_list(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        return templates.TemplateResponse(
            request, "reminders.html", {**_base_context(), "reminders": reminders},
        )

    @app.get("/reminders/new", response_class=HTMLResponse)
    async def new_reminder_form(request: Request) -> HTMLResponse:
        ctx = {
            **_base_context(),
            "reminder": None,
            "is_new": True,
            "active_days_csv": "mon,tue,wed,thu,fri",
        }
        return templates.TemplateResponse(request, "reminder_form.html", ctx)

    @app.post("/reminders")
    async def create_reminder(
        name: str = Form(...),
        message: str = Form(...),
        interval_minutes: int = Form(...),
        icon: str | None = Form(None),
        active_hours_start: str = Form("09:00"),
        active_hours_end: str = Form("18:00"),
        active_days: str = Form("mon,tue,wed,thu,fri"),
        tracked: str | None = Form(None),  # checkbox: "on" if checked, None otherwise
        unit_label: str | None = Form(None),
        unit_amount: int | None = Form(None),
        daily_goal: int | None = Form(None),
    ) -> RedirectResponse:
        is_tracked = tracked == "on"
        reminder = Reminder(
            id=None,
            name=name.strip(),
            message=message.strip(),
            icon=icon.strip() if icon else None,
            interval_minutes=interval_minutes,
            active_hours=(parse_time(active_hours_start), parse_time(active_hours_end)),
            active_days=parse_active_days(active_days),
            enabled=True,
            tracked=is_tracked,
            unit_label=(unit_label.strip() if unit_label else None) if is_tracked else None,
            unit_amount=unit_amount if is_tracked else None,
            daily_goal=daily_goal if is_tracked else None,
            created_at=datetime.now(),
            paused_until=None,
        )
        service.create_reminder(reminder)
        return RedirectResponse(url="/reminders", status_code=303)

    @app.get("/reminders/{reminder_id}/edit", response_class=HTMLResponse)
    async def edit_reminder_form(request: Request, reminder_id: int) -> HTMLResponse:
        r = service.get_reminder(reminder_id)
        if r is None:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return templates.TemplateResponse(
            request, "reminder_form.html",
            {
                **_base_context(),
                "reminder": r,
                "is_new": False,
                "active_days_csv": format_active_days(r.active_days),
            },
        )

    @app.post("/reminders/{reminder_id}")
    async def update_reminder_post(
        reminder_id: int,
        name: str = Form(...),
        message: str = Form(...),
        interval_minutes: int = Form(...),
        icon: str | None = Form(None),
        active_hours_start: str = Form("09:00"),
        active_hours_end: str = Form("18:00"),
        active_days: str = Form("mon,tue,wed,thu,fri"),
        tracked: str | None = Form(None),
        unit_label: str | None = Form(None),
        unit_amount: int | None = Form(None),
        daily_goal: int | None = Form(None),
    ) -> RedirectResponse:
        r = service.get_reminder(reminder_id)
        if r is None:
            raise HTTPException(status_code=404, detail="Reminder not found")
        is_tracked = tracked == "on"
        r.name = name.strip()
        r.message = message.strip()
        r.icon = icon.strip() if icon else None
        r.interval_minutes = interval_minutes
        r.active_hours = (parse_time(active_hours_start), parse_time(active_hours_end))
        r.active_days = parse_active_days(active_days)
        r.tracked = is_tracked
        r.unit_label = (unit_label.strip() if unit_label else None) if is_tracked else None
        r.unit_amount = unit_amount if is_tracked else None
        r.daily_goal = daily_goal if is_tracked else None
        service.update_reminder(r)
        return RedirectResponse(url="/reminders", status_code=303)

    @app.post("/reminders/{reminder_id}/delete")
    async def delete_reminder_post(reminder_id: int) -> RedirectResponse:
        service.delete_reminder(reminder_id)
        return RedirectResponse(url="/reminders", status_code=303)

    @app.get("/stats", response_class=HTMLResponse)
    async def stats_page(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        progresses = {r.id: service.daily_progress(r.id) for r in reminders if r.id is not None}
        ctx = {**_base_context(), "reminders": reminders, "progresses": progresses}
        return templates.TemplateResponse(request, "stats.html", ctx)

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request) -> HTMLResponse:
        snooze = get_setting(service._conn, "snooze_minutes", default="10")
        current_scene = get_setting(service._conn, "current_scene", default="ocean-depth")
        return templates.TemplateResponse(
            request, "settings.html",
            {
                **_base_context(),
                "snooze_minutes": snooze,
                "current_scene": current_scene,
                "available_scenes": AVAILABLE_SCENES,
            },
        )

    @app.post("/settings")
    async def settings_post(
        snooze_minutes: int = Form(...),
        current_scene: str = Form(...),
    ) -> RedirectResponse:
        if snooze_minutes < 1:
            raise HTTPException(status_code=400, detail="snooze_minutes must be >= 1")
        if current_scene not in AVAILABLE_SCENES:
            raise HTTPException(status_code=400, detail=f"Unknown scene: {current_scene}")
        set_setting(service._conn, "snooze_minutes", str(snooze_minutes))
        set_setting(service._conn, "current_scene", current_scene)
        return RedirectResponse(url="/settings", status_code=303)

    @app.post("/reminders/{reminder_id}/toggle", response_class=HTMLResponse)
    async def toggle_reminder(request: Request, reminder_id: int) -> HTMLResponse:
        r = service.get_reminder(reminder_id)
        if r is None:
            raise HTTPException(status_code=404, detail="Reminder not found")
        r.enabled = not r.enabled
        service.update_reminder(r)
        return templates.TemplateResponse(
            request, "partials/reminder_row.html", {**_base_context(), "r": r},
        )

    return app
