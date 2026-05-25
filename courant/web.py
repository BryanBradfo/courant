"""FastAPI web UI for Courant.

create_app(service) returns a FastAPI instance configured with all routes
and Jinja templates. The caller (cli.py) injects the shared ReminderService.
This keeps web.py testable in isolation (just pass a service backed by an
in-memory DB).
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from courant.events_bus import EventBus
from courant.models import Reminder, format_active_days, parse_active_days, parse_time
from courant.paths import audio_dir, videos_dir
from courant.repository import get_setting, set_setting
from courant.service import ReminderService

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
_STATIC_DIR = _PACKAGE_DIR / "static"


def _load_scenes_registry() -> dict[str, dict[str, str]]:
    """Load the video scenes registry from the bundled JSON."""
    from importlib import resources
    from typing import cast

    with resources.files("courant.data").joinpath("scenes.json").open("r") as f:
        return cast(dict[str, dict[str, str]], json.load(f))


_SCENES_REGISTRY = _load_scenes_registry()
AVAILABLE_SCENES = tuple(_SCENES_REGISTRY.keys())


def _load_audio_registry() -> dict[str, dict[str, str]]:
    """Load the audio tracks registry from the bundled JSON."""
    from importlib import resources
    from typing import cast

    with resources.files("courant.data").joinpath("audio.json").open("r") as f:
        return cast(dict[str, dict[str, str]], json.load(f))


_AUDIO_REGISTRY = _load_audio_registry()


def create_app(service: ReminderService, bus: EventBus | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if bus is not None:
            bus.bind_loop(asyncio.get_running_loop())
        yield

    app = FastAPI(
        title="Courant",
        description="A cozy reminder for developers.",
        # Disable the default /docs and /redoc — internal-only API.
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    def _base_context() -> dict[str, str]:
        raw = get_setting(service._conn, "current_scene", default="cozy-cabin")
        current_scene: str = raw or "cozy-cabin"
        return {"current_scene": current_scene}

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    videos_path = videos_dir()
    videos_path.mkdir(parents=True, exist_ok=True)
    app.mount("/videos", StaticFiles(directory=str(videos_path)), name="videos")

    audio_path = audio_dir()
    audio_path.mkdir(parents=True, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=str(audio_path)), name="audio")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/scenes")
    async def api_scenes() -> dict[str, dict[str, str]]:
        return _SCENES_REGISTRY

    @app.get("/api/audio")
    async def api_audio() -> dict[str, dict[str, str]]:
        return _AUDIO_REGISTRY

    @app.get("/api/stream")
    async def stream(request: Request) -> StreamingResponse:
        """Server-Sent Events stream for live UI notifications.

        Returns a long-lived ``text/event-stream`` connection. Each fired
        reminder is delivered as one SSE message with a JSON payload.
        Idle keepalive pings (a comment line every 15 s) keep proxies from
        timing the connection out.
        """
        if bus is None:
            raise HTTPException(status_code=503, detail="Event bus not configured")

        queue = bus.subscribe()

        async def event_generator() -> AsyncIterator[bytes]:
            try:
                yield b"retry: 2000\n\n"  # client reconnect delay
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    except TimeoutError:
                        # keepalive comment, ignored by browsers
                        yield b": keepalive\n\n"
                        continue
                    payload = json.dumps(event)
                    yield f"data: {payload}\n\n".encode()
            finally:
                bus.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # disable proxy buffering
                "Connection": "keep-alive",
            },
        )

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
        current_scene = get_setting(service._conn, "current_scene", default="cozy-cabin")
        return templates.TemplateResponse(
            request, "settings.html",
            {
                **_base_context(),
                "snooze_minutes": snooze,
                "current_scene": current_scene,
                "available_scenes": AVAILABLE_SCENES,
                "scenes_meta": _SCENES_REGISTRY,
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
