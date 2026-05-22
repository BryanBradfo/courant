# Courant — Phase 2 (Functional Web UI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a functional web UI on `localhost:8765` that lets users CRUD reminders, view stats, edit settings, and click `+1` buttons without touching SQLite directly. Uses FastAPI + Jinja + HTMX. **Strict scope:** Tailwind utility classes via CDN only — no custom CSS, no scenes, no glassmorphism (Phase 3).

**Architecture:** Single Python process. `cli.py start` boots both the scheduler (BackgroundScheduler thread, as in Phase 1) and the web server (uvicorn in main thread). They share a single `ReminderService` instance. FastAPI handlers call `service.*` methods — no SQL in `web.py`. HTMX-driven partial updates for toggle/pause/+1 interactions.

**Tech Stack additions:** `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `jinja2>=3.1`, `python-multipart>=0.0.9` (FastAPI's form parser). Already declared in `pyproject.toml` from Phase 1 bootstrap.

**Phase 2 scope:**
- New module: `courant/web.py` (FastAPI app + handlers)
- New module: `courant/web_runner.py` (uvicorn bootstrap)
- Templates: `base.html`, `dashboard.html`, `reminders.html`, `reminder_form.html`, `stats.html`, `settings.html` + partials
- Wire `cli.py _run_daemon` to start uvicorn alongside scheduler
- Tests via `httpx.AsyncClient` against the FastAPI app

**Out of scope (Phase 3):**
- Custom CSS, glassmorphism, scenes, animations
- Canvas-based particles, audio player
- Chart.js visualisations on `/stats`
- Custom fonts (Fraunces, Inter)

**Out of scope (later phases):**
- Auth/login (Phase 4 if LAN access is desired)
- Mobile-optimised layout
- WebSocket live updates

---

## File Structure

```
courant/
├── web.py                    # Task 2 — FastAPI app + route handlers
├── web_runner.py             # Task 12 — uvicorn bootstrap helper
├── templates/                # Task 2 — created with base.html
│   ├── base.html             # nav, head, Tailwind CDN, content block
│   ├── dashboard.html        # Task 3
│   ├── reminders.html        # Task 5
│   ├── reminder_form.html    # Task 6 — used for new + edit
│   ├── stats.html            # Task 10
│   ├── settings.html         # Task 11
│   └── partials/
│       ├── reminder_card.html    # Task 4 (HTMX target for toggle/pause)
│       └── reminder_row.html     # Task 5 (HTMX target for list)
├── static/                   # Task 2 — empty placeholder for now
│   └── favicon.svg           # Task 2 — minimal water drop SVG
├── cli.py                    # Modified in Task 12
tests/
└── test_web.py               # Tasks 2-11 (grows incrementally)
```

**Architectural rules (preserved from Phase 1):**
- `web.py` calls `service.*` only — no SQL, no direct `repository.*` access
- `service` instance is constructed once in `cli.py` and injected into the FastAPI app via dependency
- Templates are pure presentation — no business logic in Jinja
- HTMX partials return rendered HTML fragments, not JSON

---

## Task 1: Verify dependencies and add a couple of new ones

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Check current deps**

```bash
cd /home/wingleet/Bureau/projects/interesting/courant
source .venv/bin/activate
grep -A 5 "^dependencies" pyproject.toml
```

Confirm `apscheduler` and `desktop-notifier` are listed. `fastapi`, `uvicorn`, `jinja2`, `python-multipart` are NOT yet in deps (they were assumed in design spec but never added because Phase 1 didn't need them).

- [ ] **Step 2: Add web deps to `pyproject.toml`**

Edit the `dependencies` list to include the four FastAPI-related packages. Final deps array:

```toml
dependencies = [
    "apscheduler>=3.10",
    "desktop-notifier>=4.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
]
```

Add `httpx` to the `[project.optional-dependencies]` `dev` extras for testing:

```toml
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "freezegun>=1.4",
    "ruff>=0.4",
    "mypy>=1.10",
    "httpx>=0.27",
]
```

- [ ] **Step 3: Install the new deps**

```bash
pip install -e ".[dev]"
```

Verify uvicorn and fastapi installed:
```bash
python -c "import fastapi, uvicorn, jinja2; print(fastapi.__version__, uvicorn.__version__, jinja2.__version__)"
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat(deps): add FastAPI + uvicorn + Jinja + httpx for Phase 2 web UI"
```

---

## Task 2: FastAPI app skeleton + base template + smoke test

**Files:**
- Create: `courant/web.py`
- Create: `courant/templates/base.html`
- Create: `courant/templates/dashboard.html`
- Create: `courant/static/favicon.svg`
- Create: `tests/test_web.py`

- [ ] **Step 1: Write failing test**

`tests/test_web.py`:
```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
source .venv/bin/activate
pytest tests/test_web.py -v
```

Expected: `ModuleNotFoundError: No module named 'courant.web'`.

- [ ] **Step 3: Create `courant/web.py`**

```python
"""FastAPI web UI for Courant.

create_app(service) returns a FastAPI instance configured with all routes
and Jinja templates. The caller (cli.py) injects the shared ReminderService.
This keeps web.py testable in isolation (just pass a service backed by an
in-memory DB).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
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
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"reminders": reminders},
        )

    return app
```

- [ ] **Step 4: Create `courant/templates/base.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Courant{% endblock %}</title>
  <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <nav class="bg-white border-b border-slate-200">
    <div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
      <a href="/" class="text-xl font-semibold">Courant</a>
      <div class="flex gap-6 text-sm">
        <a href="/" class="hover:text-blue-600">Dashboard</a>
        <a href="/reminders" class="hover:text-blue-600">Reminders</a>
        <a href="/stats" class="hover:text-blue-600">Stats</a>
        <a href="/settings" class="hover:text-blue-600">Settings</a>
      </div>
    </div>
  </nav>

  <main class="max-w-4xl mx-auto px-4 py-8">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

- [ ] **Step 5: Create `courant/templates/dashboard.html`**

```html
{% extends "base.html" %}

{% block title %}Dashboard — Courant{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-6">Dashboard</h1>

{% if reminders %}
  <p class="text-slate-600">{{ reminders|length }} reminder(s) configured.</p>
{% else %}
  <p class="text-slate-600">No reminders configured yet.
    <a href="/reminders/new" class="text-blue-600 hover:underline">Add one</a>.
  </p>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: Create `courant/static/favicon.svg`**

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="#3b82f6">
  <path d="M16 4 C 10 12, 8 18, 12 24 C 16 30, 20 28, 20 22 C 20 18, 18 14, 16 4 Z"/>
</svg>
```

- [ ] **Step 7: Run tests, verify they pass**

```bash
pytest tests/test_web.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add courant/web.py courant/templates/ courant/static/ tests/test_web.py
git commit -m "feat(web): FastAPI app skeleton + dashboard + /api/health"
```

---

## Task 3: Dashboard shows reminder cards with daily progress

**Files:**
- Modify: `courant/web.py`
- Modify: `courant/templates/dashboard.html`
- Create: `courant/templates/partials/reminder_card.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Run, verify they fail** (reminders not shown)

- [ ] **Step 3: Update `courant/templates/dashboard.html`**

```html
{% extends "base.html" %}

{% block title %}Dashboard — Courant{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-6">Today</h1>

{% if reminders %}
<div class="grid gap-4 sm:grid-cols-2">
  {% for r in reminders %}
    {% set progress = progresses[r.id] %}
    {% include "partials/reminder_card.html" %}
  {% endfor %}
</div>
{% else %}
<div class="bg-white rounded-lg border border-slate-200 p-8 text-center">
  <p class="text-slate-600 mb-3">No reminders configured yet.</p>
  <a href="/reminders/new" class="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
    Add your first reminder
  </a>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Create `courant/templates/partials/reminder_card.html`**

```html
<div class="bg-white rounded-lg border border-slate-200 p-4">
  <div class="flex items-center gap-2 mb-2">
    {% if r.icon %}<span class="text-2xl">{{ r.icon }}</span>{% endif %}
    <h2 class="text-lg font-semibold">{{ r.name }}</h2>
  </div>
  {% if r.tracked and progress.goal %}
    <div class="mb-2">
      <div class="text-sm text-slate-600">{{ progress.count }} / {{ progress.goal }} {{ r.unit_label }}{{ 'es' if r.unit_label and r.unit_label.endswith('s') else 's' }}</div>
      <div class="bg-slate-100 rounded-full h-2 mt-1">
        <div class="bg-blue-500 h-2 rounded-full" style="width: {{ [progress.percent or 0, 100]|min }}%"></div>
      </div>
    </div>
  {% endif %}
  <div class="flex gap-2 mt-3">
    {% if r.tracked %}
      <button class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
        +1 {{ r.unit_label or 'done' }}
      </button>
    {% endif %}
    <button class="px-3 py-1 text-sm bg-slate-200 text-slate-700 rounded hover:bg-slate-300">
      Pause 1h
    </button>
  </div>
</div>
```

(The `+1` button will get the actual HTMX `hx-post` wiring in Task 4.)

- [ ] **Step 5: Update `web.py` dashboard handler to pass progresses**

Replace the existing `dashboard` handler:

```python
    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        progresses = {r.id: service.daily_progress(r.id) for r in reminders if r.id is not None}
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"reminders": reminders, "progresses": progresses},
        )
```

- [ ] **Step 6: Run tests, verify pass** (4 web tests total)

- [ ] **Step 7: Commit**

```bash
git add courant/web.py courant/templates/ tests/test_web.py
git commit -m "feat(web): dashboard shows reminder cards with daily progress"
```

---

## Task 4: `+1` button wired via HTMX

**Files:**
- Modify: `courant/web.py`
- Modify: `courant/templates/partials/reminder_card.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Run, verify they fail** (endpoint doesn't exist)

- [ ] **Step 3: Add endpoint to `web.py`**

Add to `create_app`:

```python
from fastapi import Form, HTTPException


    @app.post("/api/events", response_class=HTMLResponse)
    def post_event(
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
```

- [ ] **Step 4: Wire HTMX on the `+1` button**

Edit `courant/templates/partials/reminder_card.html` — wrap the card in an `id` and add HTMX attrs:

```html
<div class="bg-white rounded-lg border border-slate-200 p-4" id="reminder-card-{{ r.id }}">
  <div class="flex items-center gap-2 mb-2">
    {% if r.icon %}<span class="text-2xl">{{ r.icon }}</span>{% endif %}
    <h2 class="text-lg font-semibold">{{ r.name }}</h2>
  </div>
  {% if r.tracked and progress.goal %}
    <div class="mb-2">
      <div class="text-sm text-slate-600">{{ progress.count }} / {{ progress.goal }} {{ r.unit_label }}{{ 'es' if r.unit_label and r.unit_label.endswith('s') else 's' }}</div>
      <div class="bg-slate-100 rounded-full h-2 mt-1">
        <div class="bg-blue-500 h-2 rounded-full" style="width: {{ [progress.percent or 0, 100]|min }}%"></div>
      </div>
    </div>
  {% endif %}
  <div class="flex gap-2 mt-3">
    {% if r.tracked %}
      <button
        hx-post="/api/events"
        hx-vals='{"reminder_id": {{ r.id }}, "kind": "ack"}'
        hx-target="#reminder-card-{{ r.id }}"
        hx-swap="outerHTML"
        class="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        +1 {{ r.unit_label or 'done' }}
      </button>
    {% endif %}
    <button class="px-3 py-1 text-sm bg-slate-200 text-slate-700 rounded hover:bg-slate-300">
      Pause 1h
    </button>
  </div>
</div>
```

- [ ] **Step 5: Run tests, verify pass** (6 web tests)

- [ ] **Step 6: Commit**

```bash
git add courant/web.py courant/templates/ tests/test_web.py
git commit -m "feat(web): +1 button posts to /api/events and HTMX-swaps card"
```

---

## Task 5: `/reminders` list page

**Files:**
- Modify: `courant/web.py`
- Create: `courant/templates/reminders.html`
- Create: `courant/templates/partials/reminder_row.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handler to `web.py`**

```python
    @app.get("/reminders", response_class=HTMLResponse)
    def reminders_list(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        return templates.TemplateResponse(
            request, "reminders.html", {"reminders": reminders},
        )
```

- [ ] **Step 4: Create `courant/templates/reminders.html`**

```html
{% extends "base.html" %}

{% block title %}Reminders — Courant{% endblock %}

{% block content %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-bold">Reminders</h1>
  <a href="/reminders/new" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
    New reminder
  </a>
</div>

{% if reminders %}
<div class="bg-white rounded-lg border border-slate-200 divide-y divide-slate-200">
  {% for r in reminders %}
    {% include "partials/reminder_row.html" %}
  {% endfor %}
</div>
{% else %}
<div class="bg-white rounded-lg border border-slate-200 p-8 text-center">
  <p class="text-slate-600">No reminders yet. Click "New reminder" to add one.</p>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Create `courant/templates/partials/reminder_row.html`**

```html
<div class="flex items-center justify-between p-4" id="reminder-row-{{ r.id }}">
  <div class="flex items-center gap-3">
    {% if r.icon %}<span class="text-xl">{{ r.icon }}</span>{% endif %}
    <div>
      <div class="font-medium">{{ r.name }}</div>
      <div class="text-sm text-slate-500">
        Every {{ r.interval_minutes }} min
        {% if r.tracked %} · tracked ({{ r.daily_goal }}/day){% endif %}
        {% if not r.enabled %} · <span class="text-amber-600">disabled</span>{% endif %}
      </div>
    </div>
  </div>
  <div class="flex items-center gap-2">
    <a href="/reminders/{{ r.id }}/edit" class="text-sm text-blue-600 hover:underline">Edit</a>
    <form method="post" action="/reminders/{{ r.id }}/delete" class="inline">
      <button type="submit" class="text-sm text-red-600 hover:underline"
              onclick="return confirm('Delete &quot;{{ r.name }}&quot; and all its events ?')">
        Delete
      </button>
    </form>
  </div>
</div>
```

- [ ] **Step 6: Run tests, verify pass** (8 web tests)

- [ ] **Step 7: Commit**

```bash
git add courant/web.py courant/templates/ tests/test_web.py
git commit -m "feat(web): /reminders page lists all with edit/delete actions"
```

---

## Task 6: New reminder form (GET) + create (POST)

**Files:**
- Modify: `courant/web.py`
- Create: `courant/templates/reminder_form.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handlers to `web.py`**

Add imports at top of `web.py`:
```python
from datetime import datetime
from fastapi.responses import RedirectResponse
from courant.models import Reminder, parse_active_days, parse_time
```

Add handlers inside `create_app`:

```python
    @app.get("/reminders/new", response_class=HTMLResponse)
    def new_reminder_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "reminder_form.html",
            {"reminder": None, "is_new": True, "active_days_csv": "mon,tue,wed,thu,fri"},
        )

    @app.post("/reminders")
    def create_reminder(
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
```

- [ ] **Step 4: Create `courant/templates/reminder_form.html`**

```html
{% extends "base.html" %}

{% block title %}{{ 'New' if is_new else 'Edit' }} reminder — Courant{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-6">{{ 'New' if is_new else 'Edit' }} reminder</h1>

<form method="post"
      action="{{ '/reminders' if is_new else '/reminders/' ~ reminder.id }}"
      class="bg-white rounded-lg border border-slate-200 p-6 space-y-4 max-w-2xl">

  <div>
    <label class="block text-sm font-medium mb-1">Name</label>
    <input name="name" required value="{{ reminder.name if reminder else '' }}"
           class="w-full border border-slate-300 rounded px-3 py-2">
  </div>

  <div>
    <label class="block text-sm font-medium mb-1">Message</label>
    <input name="message" required value="{{ reminder.message if reminder else '' }}"
           class="w-full border border-slate-300 rounded px-3 py-2">
  </div>

  <div class="grid grid-cols-2 gap-4">
    <div>
      <label class="block text-sm font-medium mb-1">Icon (emoji)</label>
      <input name="icon" value="{{ reminder.icon if reminder else '' }}" maxlength="4"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
    <div>
      <label class="block text-sm font-medium mb-1">Every X minutes</label>
      <input name="interval_minutes" type="number" min="1" required
             value="{{ reminder.interval_minutes if reminder else 45 }}"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
  </div>

  <div class="grid grid-cols-2 gap-4">
    <div>
      <label class="block text-sm font-medium mb-1">Active from</label>
      <input name="active_hours_start" type="time" required
             value="{{ '%02d:%02d'|format(reminder.active_hours[0].hour, reminder.active_hours[0].minute) if reminder else '09:00' }}"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
    <div>
      <label class="block text-sm font-medium mb-1">Active until</label>
      <input name="active_hours_end" type="time" required
             value="{{ '%02d:%02d'|format(reminder.active_hours[1].hour, reminder.active_hours[1].minute) if reminder else '18:00' }}"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
  </div>

  <div>
    <label class="block text-sm font-medium mb-1">Active days (comma-separated)</label>
    <input name="active_days"
           value="{{ active_days_csv }}"
           class="w-full border border-slate-300 rounded px-3 py-2">
    <p class="text-xs text-slate-500 mt-1">Use abbreviations: mon, tue, wed, thu, fri, sat, sun</p>
  </div>

  <div class="border-t border-slate-200 pt-4">
    <label class="flex items-center gap-2">
      <input type="checkbox" name="tracked" value="on"
             {% if reminder and reminder.tracked %}checked{% endif %}>
      <span class="text-sm font-medium">Track progress toward a daily goal</span>
    </label>
  </div>

  <div class="grid grid-cols-3 gap-4">
    <div>
      <label class="block text-sm font-medium mb-1">Unit label</label>
      <input name="unit_label" placeholder="glass, cup..."
             value="{{ reminder.unit_label if reminder and reminder.unit_label else '' }}"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
    <div>
      <label class="block text-sm font-medium mb-1">Unit amount</label>
      <input name="unit_amount" type="number" min="1" placeholder="250"
             value="{{ reminder.unit_amount if reminder and reminder.unit_amount else '' }}"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
    <div>
      <label class="block text-sm font-medium mb-1">Daily goal</label>
      <input name="daily_goal" type="number" min="1" placeholder="8"
             value="{{ reminder.daily_goal if reminder and reminder.daily_goal else '' }}"
             class="w-full border border-slate-300 rounded px-3 py-2">
    </div>
  </div>

  <div class="flex gap-3 pt-4 border-t border-slate-200">
    <button type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
      {{ 'Create' if is_new else 'Save' }}
    </button>
    <a href="/reminders" class="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300">
      Cancel
    </a>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 5: Run tests, verify pass** (11 web tests)

- [ ] **Step 6: Commit**

```bash
git add courant/web.py courant/templates/ tests/test_web.py
git commit -m "feat(web): new reminder form + POST /reminders creates"
```

---

## Task 7: Edit reminder (GET + POST)

**Files:**
- Modify: `courant/web.py`
- Modify: `tests/test_web.py`

(Reuses `reminder_form.html` from Task 6.)

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handlers to `web.py`**

```python
    @app.get("/reminders/{reminder_id}/edit", response_class=HTMLResponse)
    def edit_reminder_form(request: Request, reminder_id: int) -> HTMLResponse:
        from courant.models import format_active_days
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
    def update_reminder_post(
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
```

- [ ] **Step 4: Run tests, verify pass** (14 web tests)

- [ ] **Step 5: Commit**

```bash
git add courant/web.py tests/test_web.py
git commit -m "feat(web): edit reminder form + POST update"
```

---

## Task 8: Delete reminder

**Files:**
- Modify: `courant/web.py`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
async def test_delete_reminder(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    rid = service.create_reminder(_make_reminder("Water"))
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/reminders/{rid}/delete", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert service.get_reminder(rid) is None
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handler**

```python
    @app.post("/reminders/{reminder_id}/delete")
    def delete_reminder_post(reminder_id: int) -> RedirectResponse:
        service.delete_reminder(reminder_id)
        return RedirectResponse(url="/reminders", status_code=303)
```

- [ ] **Step 4: Verify pass** (15 web tests)

- [ ] **Step 5: Commit**

```bash
git add courant/web.py tests/test_web.py
git commit -m "feat(web): delete reminder via POST"
```

---

## Task 9: Toggle enable/disable (HTMX)

**Files:**
- Modify: `courant/web.py`
- Modify: `courant/templates/partials/reminder_row.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handler**

```python
    @app.post("/reminders/{reminder_id}/toggle", response_class=HTMLResponse)
    def toggle_reminder(request: Request, reminder_id: int) -> HTMLResponse:
        r = service.get_reminder(reminder_id)
        if r is None:
            raise HTTPException(status_code=404, detail="Reminder not found")
        r.enabled = not r.enabled
        service.update_reminder(r)
        return templates.TemplateResponse(
            request, "partials/reminder_row.html", {"r": r},
        )
```

- [ ] **Step 4: Update reminder_row.html with toggle button**

Edit `courant/templates/partials/reminder_row.html` — add the toggle button between Edit and Delete:

```html
    <button
      hx-post="/reminders/{{ r.id }}/toggle"
      hx-target="#reminder-row-{{ r.id }}"
      hx-swap="outerHTML"
      class="text-sm {{ 'text-amber-600' if r.enabled else 'text-green-600' }} hover:underline">
      {{ 'Disable' if r.enabled else 'Enable' }}
    </button>
```

Place between the `Edit` link and `Delete` form.

- [ ] **Step 5: Verify pass** (16 web tests)

- [ ] **Step 6: Commit**

```bash
git add courant/web.py courant/templates/partials/reminder_row.html tests/test_web.py
git commit -m "feat(web): HTMX toggle enable/disable on reminders list"
```

---

## Task 10: `/stats` page (basic numbers, no chart)

**Files:**
- Modify: `courant/web.py`
- Create: `courant/templates/stats.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handler**

```python
    @app.get("/stats", response_class=HTMLResponse)
    def stats_page(request: Request) -> HTMLResponse:
        reminders = service.list_reminders()
        progresses = {r.id: service.daily_progress(r.id) for r in reminders if r.id is not None}
        return templates.TemplateResponse(
            request, "stats.html", {"reminders": reminders, "progresses": progresses},
        )
```

- [ ] **Step 4: Create `courant/templates/stats.html`**

```html
{% extends "base.html" %}

{% block title %}Stats — Courant{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-6">Today's stats</h1>

{% if reminders %}
<div class="bg-white rounded-lg border border-slate-200 divide-y divide-slate-200">
  {% for r in reminders %}
    {% set progress = progresses[r.id] %}
    <div class="flex items-center justify-between p-4">
      <div class="flex items-center gap-3">
        {% if r.icon %}<span class="text-xl">{{ r.icon }}</span>{% endif %}
        <span class="font-medium">{{ r.name }}</span>
      </div>
      <div class="text-right">
        <div class="text-2xl font-semibold">
          {{ progress.count }}{% if progress.goal %} / {{ progress.goal }}{% endif %}
        </div>
        {% if progress.percent is not none %}
          <div class="text-sm text-slate-500">{{ "%.0f"|format(progress.percent) }}%</div>
        {% else %}
          <div class="text-sm text-slate-500">not tracked</div>
        {% endif %}
      </div>
    </div>
  {% endfor %}
</div>
<p class="text-sm text-slate-500 mt-4">
  Weekly/monthly aggregates and charts coming in Phase 3.
</p>
{% else %}
<p class="text-slate-600">No reminders configured.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Verify pass** (17 web tests)

- [ ] **Step 6: Commit**

```bash
git add courant/web.py courant/templates/ tests/test_web.py
git commit -m "feat(web): /stats page with per-reminder daily counts"
```

---

## Task 11: `/settings` page (snooze minutes)

**Files:**
- Modify: `courant/web.py`
- Create: `courant/templates/settings.html`
- Modify: `tests/test_web.py`

- [ ] **Step 1: Append tests**

```python
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
```

- [ ] **Step 2: Verify fail**

- [ ] **Step 3: Add handlers**

```python
from courant.repository import get_setting, set_setting


    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request) -> HTMLResponse:
        snooze = get_setting(service._conn, "snooze_minutes", default="10")
        return templates.TemplateResponse(
            request, "settings.html", {"snooze_minutes": snooze},
        )

    @app.post("/settings")
    def settings_post(
        snooze_minutes: int = Form(...),
    ) -> RedirectResponse:
        if snooze_minutes < 1:
            raise HTTPException(status_code=400, detail="snooze_minutes must be >= 1")
        set_setting(service._conn, "snooze_minutes", str(snooze_minutes))
        return RedirectResponse(url="/settings", status_code=303)
```

(Note: accessing `service._conn` is a small abstraction break. For Phase 2 we accept it. A Phase 4 cleanup could add `service.get_setting()` / `service.set_setting()` methods to formalize.)

- [ ] **Step 4: Create `courant/templates/settings.html`**

```html
{% extends "base.html" %}

{% block title %}Settings — Courant{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-6">Settings</h1>

<form method="post" action="/settings"
      class="bg-white rounded-lg border border-slate-200 p-6 space-y-4 max-w-md">
  <div>
    <label class="block text-sm font-medium mb-1">
      Snooze duration (minutes)
    </label>
    <input name="snooze_minutes" type="number" min="1" required
           value="{{ snooze_minutes }}"
           class="w-full border border-slate-300 rounded px-3 py-2">
    <p class="text-xs text-slate-500 mt-1">
      How long to delay a reminder when you click "Snooze" on a notification.
    </p>
  </div>

  <div class="pt-4 border-t border-slate-200">
    <button type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
      Save
    </button>
  </div>
</form>

<p class="text-sm text-slate-500 mt-6">
  More settings (theme, notification timeout, scene selection) coming in Phase 3.
</p>
{% endblock %}
```

- [ ] **Step 5: Verify pass** (19 web tests)

- [ ] **Step 6: Commit**

```bash
git add courant/web.py courant/templates/ tests/test_web.py
git commit -m "feat(web): /settings page with snooze duration"
```

---

## Task 12: Wire uvicorn into `cli.py start`

**Files:**
- Create: `courant/web_runner.py`
- Modify: `courant/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Create `courant/web_runner.py`**

```python
"""Helpers to run the FastAPI app via uvicorn.

Kept separate from web.py so `web.py` stays pure FastAPI / no uvicorn config —
testable with httpx.AsyncClient without spinning a real server.
"""
from __future__ import annotations

import logging

import uvicorn

from courant.web import create_app
from courant.service import ReminderService

logger = logging.getLogger(__name__)


def run_server(
    service: ReminderService,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    """Block until uvicorn shuts down (SIGINT/SIGTERM)."""
    app = create_app(service)
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,  # very noisy at every HTMX poll
    )
    server = uvicorn.Server(config)
    logger.info("Web UI listening on http://%s:%d", host, port)
    server.run()
```

- [ ] **Step 2: Update `_run_daemon` in `cli.py`**

Find the current `_run_daemon` and replace its body:

```python
def _run_daemon() -> int:
    _setup_logging()
    backup_if_stale(db_path())
    conn = connect(str(db_path()))
    migrate(conn)

    service = ReminderService(conn)
    seeded = service.seed_defaults_if_empty()
    if seeded:
        logger.info("Seeded %d default reminders on first launch", seeded)

    notifier = _build_notifier()
    apsched = BackgroundScheduler()
    rs = ReminderScheduler(scheduler=apsched, service=service, notifier=notifier)
    rs.sync_jobs()
    rs.start()

    logger.info("Courant daemon started (PID %d)", os.getpid())

    try:
        # uvicorn handles SIGTERM/SIGINT internally and returns cleanly
        from courant.web_runner import run_server
        run_server(service)
    finally:
        rs.shutdown()
        conn.close()
    return 0
```

Remove the old SIGTERM/SIGINT handler and the `while not stop_requested: time.sleep(0.5)` loop — uvicorn handles signals for us.

You can also remove these imports if they're no longer used: `signal`, `time as time_module`.

- [ ] **Step 3: Add smoke test in `tests/test_cli.py`**

Update the existing `test_start_creates_db_and_seeds_default_reminders` to also verify the web server is responding:

```python
def test_start_serves_health_endpoint(
    isolated_paths: Path, tmp_path: Path,
):
    """Start the daemon, hit /api/health, then shut it down."""
    import urllib.request
    import urllib.error

    env = {
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "PATH": os.environ.get("PATH", ""),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "courant.cli", "start"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        # Poll /api/health for up to 5s
        ready = False
        for _ in range(50):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=0.5) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        assert ready, "Web server did not respond within 5s"
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
```

(Add `import os, signal, time` at the top of test_cli.py if not already.)

- [ ] **Step 4: Run all tests**

```bash
source .venv/bin/activate
pytest -v
```

Expected: all previous tests + new web tests + new CLI smoke test pass. Total ~85+.

- [ ] **Step 5: Lint + types**

```bash
ruff check courant tests
mypy courant
```

Fix any issues. Likely candidates: unused imports after removing the old `_run_daemon` body, or mypy complaints about uvicorn's untyped imports (add `# type: ignore[import-untyped]` if needed).

- [ ] **Step 6: Commit**

```bash
git add courant/web_runner.py courant/cli.py tests/test_cli.py
git commit -m "feat(cli): start command runs the web UI via uvicorn"
```

---

## Task 13: Manual E2E + README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Manual smoke**

```bash
source .venv/bin/activate
courant start
```

In a browser, visit `http://localhost:8765` and verify :

- Dashboard shows 3 cards (the seeded reminders : Drink water, Eye break, Stretch)
- Drink water card shows `0 / 8` progress
- Click `+1 glass` → progress jumps to `1 / 8` without page reload (HTMX swap)
- Navigate to `/reminders` → list view with edit/delete/toggle buttons
- Click `Disable` on one → row updates inline, shows "Enable" button
- Click `New reminder` → form renders
- Submit form with `name=Test reminder, message=Hi, interval_minutes=10` → redirects to list, "Test reminder" appears
- Click `Delete` → confirm dialog, then row disappears
- Navigate to `/stats` → shows per-reminder counts
- Navigate to `/settings` → shows `Snooze duration: 10`, edit to 15, submit, page reloads with 15

Stop with Ctrl+C.

- [ ] **Step 2: Update README status section**

```markdown
## Status

- ✅ Phase 1 — Core CLI + desktop notifications working end-to-end
- ✅ Phase 2 — Functional web UI (FastAPI + HTMX, Tailwind utility classes)
- ⏳ Phase 3 — Cozy aesthetic with ambient scenes (rain, ocean, sunset…)
- ⏳ Phase 4 — Polish, systemd integration, PyPI release
```

Add a short "Usage" section after "Quick start" :

```markdown
## Usage

After `courant start`, point your browser at <http://localhost:8765> :

- **Dashboard** — see each reminder's daily progress and click `+1` to log a hit
- **Reminders** — create / edit / disable / delete reminders
- **Stats** — daily progress per reminder
- **Settings** — global preferences (e.g. snooze duration)

Notifications fire on the desktop via D-Bus as configured. Clicking a notification action ("+1 glass" or "Snooze 10 min") records an event in the same database the web UI reads from — both views stay in sync.
```

- [ ] **Step 3: Commit and tag**

```bash
git add README.md
git commit -m "docs: mark Phase 2 complete and document web UI usage"
git tag -a phase-2-complete -m "Phase 2: Functional web UI (FastAPI + HTMX)"
```

- [ ] **Step 4: Push and verify CI**

```bash
git push origin main
git push origin phase-2-complete
gh run watch $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
```

- [ ] **Step 5: Optional GitHub release**

```bash
gh release create phase-2-complete \
  --title "Phase 2 — Functional Web UI" \
  --notes "Adds a basic but fully functional web UI at localhost:8765 : dashboard with daily progress, reminder CRUD, stats, and settings. Tailwind utility classes only — Phase 3 will add the cozy aesthetic with ambient scenes and glassmorphism."
```

---

## Phase 2 Done ✓

At Phase 2 completion the daemon :
- Still does everything Phase 1 did (notifications, scheduling, persistence)
- Plus a functional web UI on `localhost:8765` for CRUD, stats, settings
- HTMX-driven for snappy interactions (no page reloads for +1 / toggle)
- ~85 tests, ruff/mypy clean
- CI green on Python 3.11/3.12/3.13

**Next phase :** `docs/superpowers/plans/YYYY-MM-DD-courant-phase-3-aesthetic.md` for the cozy lo-fi visual transformation (scenes, glassmorphism, fonts, animations, audio player).
