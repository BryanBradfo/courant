"""FastAPI web UI for Courant.

create_app(service) returns a FastAPI instance configured with all routes
and Jinja templates. The caller (cli.py) injects the shared ReminderService.
This keeps web.py testable in isolation (just pass a service backed by an
in-memory DB).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

    return app
