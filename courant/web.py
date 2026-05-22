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
from courant.service import ReminderService

_PACKAGE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"


def create_app(service: ReminderService) -> FastAPI:
    app = FastAPI(
        title="Courant",
        description="A cozy reminder for developers.",
        # Disable the default /docs and /redoc — internal-only API.
        docs_url=None,
        redoc_url=None,
    )

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
            {"reminders": reminders, "progresses": progresses},
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
            {"r": r, "progress": progress},
        )

    @app.get("/reminders", response_class=HTMLResponse)
    async def reminders_list(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        return templates.TemplateResponse(
            request, "reminders.html", {"reminders": reminders},
        )

    @app.get("/reminders/new", response_class=HTMLResponse)
    async def new_reminder_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "reminder_form.html",
            {"reminder": None, "is_new": True, "active_days_csv": "mon,tue,wed,thu,fri"},
        )

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

    return app
