# Courant — Phase 3 (Cozy Aesthetic) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the bare-Tailwind Phase 2 UI into a cozy, lo-fi, studywithme.io-inspired interface. Full-screen ambient scenes (rain on a window, ocean depth, sunset beach, forest stream, calm night), a centered glassmorphism panel, custom typography (Fraunces + Inter), gentle animations. Each scene is a self-contained CSS+Canvas module that contributors can add via a single file.

**Architecture:** Pure frontend transformation. Backend (`web.py`, `service.py`, `repository.py`) stays untouched. We add a CSS file (`static/courant.css`), a scene framework (`static/scenes/*.js`), a tiny scene-loader (`static/scene-loader.js`), and rework templates to use the new layout. Persistence : selected scene is stored in `settings` via the existing `get_setting` / `set_setting`.

**Tech Stack additions:** Google Fonts (Fraunces serif + Inter sans-serif, loaded via CDN). No build step ; CSS is hand-written, JS is vanilla modules. Tailwind CDN stays for utility classes.

**Phase 3 scope (this plan):**
- Typography + CSS framework (`courant.css`)
- Glassmorphism panel + new dashboard layout
- Scene framework with the 5 v1 scenes (ocean-depth, rainy-window, sunset-beach, forest-stream, calm-night)
- Scene selector (top-right dropdown) with persistence
- Animations (button splash, panel appear, scene crossfade)
- `prefers-reduced-motion` respect
- `docs/ADDING_A_SCENE.md` contributor guide
- README screenshots + Phase 3 status

**Out of scope (Phase 4):**
- Audio player + lo-fi ambient sounds
- systemd integration
- PyPI publish
- Mobile-responsive layout (current desktop-first is fine)

---

## File Structure

```
courant/
├── static/
│   ├── courant.css                     # NEW : core stylesheet (palette, typography, panel, layout)
│   ├── scene-loader.js                 # NEW : dynamically loads/switches scene modules
│   └── scenes/                         # NEW : one .js file per scene
│       ├── ocean-depth.js              # Task 6 (validates pattern)
│       ├── rainy-window.js             # Task 10
│       ├── sunset-beach.js             # Task 11
│       ├── forest-stream.js            # Task 12
│       └── calm-night.js               # Task 13
├── templates/
│   ├── base.html                       # Modified : add fonts, scene canvas, scene selector slot
│   ├── dashboard.html                  # Modified : panel layout
│   ├── reminders.html                  # Modified : panel layout
│   ├── reminder_form.html              # Modified : panel layout
│   ├── stats.html                      # Modified : panel layout
│   ├── settings.html                   # Modified : add scene selector if not in nav
│   └── partials/
│       ├── reminder_card.html          # Modified : cozy styling
│       └── reminder_row.html           # Modified : cozy styling
├── web.py                              # Modified : pass current_scene to all template responses
docs/
└── ADDING_A_SCENE.md                   # NEW : contributor guide (Task 18)
```

**Architectural rules:**
- The scene framework lives entirely client-side ; `web.py` only stores/reads the **name** of the selected scene
- A scene is a JS module with the shape `{ init(canvas, ctx), cleanup(), theme: 'dark' | 'light' }`
- The scene-loader handles dynamic import, crossfade between scenes, and dispatching the theme class on `<body>`
- CSS is split semantically : `:root` variables (palette, typography) → base elements → components (panel, cards) → utilities. No utility-class soup in the custom CSS.

---

## Task 1 : CSS framework and typography

**Files:**
- Create: `courant/static/courant.css`
- Modify: `courant/templates/base.html`

- [ ] **Step 1 : Create `courant/static/courant.css` with the foundation**

```css
/* Courant — cozy aesthetic stylesheet.
   Loaded after Tailwind CDN, so :root vars and class rules win on specificity ties. */

:root {
  /* Fonts */
  --font-display: 'Fraunces', 'Playfair Display', Georgia, serif;
  --font-ui:      'Inter', system-ui, -apple-system, sans-serif;
  --font-mono:    'JetBrains Mono', ui-monospace, monospace;

  /* Neutral text colors — overridden per scene-theme */
  --text-primary:   #f5f5f5;
  --text-secondary: rgba(245, 245, 245, 0.7);
  --text-muted:     rgba(245, 245, 245, 0.5);

  /* Panel glassmorphism */
  --panel-bg:     rgba(255, 255, 255, 0.08);
  --panel-border: rgba(255, 255, 255, 0.18);
  --panel-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  --panel-radius: 24px;
  --panel-blur:   20px;

  /* Accent colors — used by buttons, progress bars, etc. */
  --accent-blue:  #60a5fa;
  --accent-blue-hover: #3b82f6;
}

/* Light-scene overrides */
.scene-light {
  --panel-bg:     rgba(10, 20, 40, 0.35);
  --panel-border: rgba(255, 255, 255, 0.25);
}

/* Reset Tailwind body styles for our layout */
body {
  font-family: var(--font-ui);
  color: var(--text-primary);
  background: #0a0a0a;  /* black until a scene loads */
  min-height: 100vh;
  overflow-x: hidden;
}

/* Scene canvas takes the full viewport, sits behind everything */
#scene-canvas {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  z-index: -1;
  transition: opacity 800ms ease-in-out;
}

/* Top nav, transparent so the scene shows through */
.cozy-nav {
  position: relative;
  z-index: 10;
  background: transparent;
  border-bottom: none;
  padding: 1.5rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-primary);
}

.cozy-nav a { color: var(--text-secondary); }
.cozy-nav a:hover { color: var(--text-primary); }
.cozy-nav .brand {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

/* Display headings */
.display-1 { font-family: var(--font-display); font-weight: 600; font-size: 2.25rem; letter-spacing: -0.02em; }
.display-2 { font-family: var(--font-display); font-weight: 500; font-size: 1.5rem; letter-spacing: -0.015em; }

/* Glassmorphism panel — the central container of every page */
.panel {
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: var(--panel-radius);
  box-shadow: var(--panel-shadow);
  backdrop-filter: blur(var(--panel-blur)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--panel-blur)) saturate(140%);
  padding: 2.5rem;
  color: var(--text-primary);
  animation: panel-appear 600ms cubic-bezier(0.22, 1, 0.36, 1) backwards;
}

.panel-narrow { max-width: 520px; }
.panel-wide   { max-width: 760px; }

/* Subtle panel-appear animation on page load */
@keyframes panel-appear {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Reduce or disable animations for users who ask */
@media (prefers-reduced-motion: reduce) {
  .panel { animation: none; }
  #scene-canvas { transition: none; }
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}

/* Cozy button — used inside panels */
.btn-cozy {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border-radius: 999px;
  font-family: var(--font-ui);
  font-weight: 500;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  transition: background 150ms, transform 150ms;
}
.btn-cozy:hover { background: rgba(255, 255, 255, 0.2); }
.btn-cozy:active { transform: scale(0.97); }

.btn-cozy-primary {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
}
.btn-cozy-primary:hover { background: var(--accent-blue-hover); }

/* Progress bar inside reminder cards */
.progress-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent-blue);
  border-radius: 999px;
  transition: width 600ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* Splash animation on +1 button click */
@keyframes splash {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.15); }
  100% { transform: scale(1); }
}
.btn-cozy.splashing { animation: splash 600ms ease-out; }

/* Form inputs inside panels */
.panel input[type="text"],
.panel input[type="time"],
.panel input[type="number"],
.panel textarea {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 0.625rem 0.875rem;
  color: var(--text-primary);
  font-family: var(--font-ui);
  width: 100%;
  transition: border-color 150ms, background 150ms;
}
.panel input:focus, .panel textarea:focus {
  outline: none;
  border-color: var(--accent-blue);
  background: rgba(255, 255, 255, 0.12);
}
.panel label { color: var(--text-secondary); font-size: 0.875rem; }
```

- [ ] **Step 2 : Update `courant/templates/base.html`** to load Google Fonts + the new stylesheet

Replace the existing `<head>` section with :

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Courant{% endblock %}</title>
  <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">

  <!-- Tailwind for utility classes still in use elsewhere -->
  <script src="https://cdn.tailwindcss.com"></script>

  <!-- Google Fonts : Fraunces for display, Inter for UI -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

  <!-- Courant cozy stylesheet -->
  <link rel="stylesheet" href="/static/courant.css">

  <!-- HTMX for interactivity -->
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <!-- existing nav and main -->
</body>
</html>
```

- [ ] **Step 3 : Smoke check**

Run `pytest -q` — expect all 84 tests still pass (we only added static assets).

- [ ] **Step 4 : Commit**

```bash
git add courant/static/courant.css courant/templates/base.html
git commit -m "feat(css): cozy stylesheet foundation + Google Fonts + reduced-motion"
```

---

## Task 2 : Scene canvas + scene-loader skeleton

**Files:**
- Create: `courant/static/scene-loader.js`
- Modify: `courant/templates/base.html`
- Modify: `courant/web.py` (passes `current_scene` to all template responses)

- [ ] **Step 1 : Create `courant/static/scene-loader.js`**

```javascript
// scene-loader.js — dynamically loads scene modules and renders them on #scene-canvas.
//
// A scene module exports default object {
//   init(canvas, ctx),  // start animation loop, return cleanup function
//   theme: 'dark' | 'light',
// }
//
// init() should call requestAnimationFrame internally and return a cleanup fn
// that cancels the loop. The loader manages crossfade between scenes.

const canvas = document.getElementById('scene-canvas');
if (canvas) {
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
}

let currentCleanup = null;

function resizeCanvas() {
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = window.innerWidth * dpr;
  canvas.height = window.innerHeight * dpr;
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  const ctx = canvas.getContext('2d');
  if (ctx) ctx.scale(dpr, dpr);
}

async function loadScene(name) {
  if (!canvas) return;

  // Tear down previous scene
  if (currentCleanup) {
    try { currentCleanup(); } catch (e) { console.warn('scene cleanup error', e); }
    currentCleanup = null;
  }

  // Crossfade: fade out, swap, fade in
  canvas.style.opacity = '0';
  await new Promise(resolve => setTimeout(resolve, 400));

  // Clear canvas
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  let module;
  try {
    module = await import(`/static/scenes/${name}.js`);
  } catch (e) {
    console.error(`Failed to load scene "${name}"`, e);
    canvas.style.opacity = '1';
    return;
  }

  const scene = module.default;
  document.body.classList.remove('scene-dark', 'scene-light');
  document.body.classList.add(scene.theme === 'light' ? 'scene-light' : 'scene-dark');

  currentCleanup = scene.init(canvas, ctx);
  canvas.style.opacity = '1';
}

// Boot: read scene from body data attribute (server-rendered)
const initialScene = document.body.dataset.scene || 'ocean-depth';
loadScene(initialScene);

// Pause animations when tab is hidden
document.addEventListener('visibilitychange', () => {
  if (document.hidden && currentCleanup) {
    currentCleanup();
    currentCleanup = null;
  } else if (!document.hidden && !currentCleanup) {
    loadScene(document.body.dataset.scene || 'ocean-depth');
  }
});

// Expose for the scene selector
window.courantLoadScene = loadScene;
```

- [ ] **Step 2 : Update `base.html`** to inject the canvas and load the script

Replace the `<body>` opening and add the canvas + script :

```html
<body class="scene-dark"
      data-scene="{{ current_scene or 'ocean-depth' }}">
  <canvas id="scene-canvas"></canvas>

  <nav class="cozy-nav">
    <a href="/" class="brand">Courant</a>
    <div class="flex gap-6 text-sm">
      <a href="/">Dashboard</a>
      <a href="/reminders">Reminders</a>
      <a href="/stats">Stats</a>
      <a href="/settings">Settings</a>
    </div>
  </nav>

  <main class="max-w-4xl mx-auto px-4 py-8">
    {% block content %}{% endblock %}
  </main>

  <script type="module" src="/static/scene-loader.js"></script>
</body>
```

- [ ] **Step 3 : Update `courant/web.py`** to pass `current_scene` to every template response

Add a helper at the top of `create_app` :

```python
def _base_context() -> dict[str, str]:
    current_scene = get_setting(service._conn, "current_scene", default="ocean-depth")
    return {"current_scene": current_scene}
```

Then in each `TemplateResponse(...)` call, merge `_base_context()` into the context dict :

```python
return templates.TemplateResponse(
    request, "dashboard.html",
    {**_base_context(), "reminders": reminders, "progresses": progresses},
)
```

Do this for every handler that renders a template : dashboard, reminders_list, new_reminder_form, edit_reminder_form, stats_page, settings_page, and the HTMX partial responses (post_event, toggle_reminder).

- [ ] **Step 4 : Run tests**

```bash
pytest -v
```

All 84 tests should still pass (we added a context field but nothing breaks).

- [ ] **Step 5 : Commit**

```bash
git add courant/static/scene-loader.js courant/templates/base.html courant/web.py
git commit -m "feat(scene): scene-loader framework + canvas in base layout"
```

---

## Task 3 : Glassmorphism panel layout for dashboard

**Files:**
- Modify: `courant/templates/dashboard.html`
- Modify: `courant/templates/partials/reminder_card.html`

- [ ] **Step 1 : Restyle `dashboard.html`**

```html
{% extends "base.html" %}

{% block title %}Dashboard — Courant{% endblock %}

{% block content %}
<div class="flex justify-center pt-12">
  <div class="panel panel-narrow w-full">
    <div class="flex items-baseline justify-between mb-6">
      <h1 class="display-1">Today</h1>
      <span class="text-sm" style="color: var(--text-muted)">
        {{ reminders|length }} reminder{{ 's' if reminders|length != 1 else '' }}
      </span>
    </div>

    {% if reminders %}
      <div class="space-y-4">
        {% for r in reminders %}
          {% set progress = progresses[r.id] %}
          {% include "partials/reminder_card.html" %}
        {% endfor %}
      </div>
    {% else %}
      <div class="text-center py-8">
        <p style="color: var(--text-secondary)" class="mb-4">No reminders configured yet.</p>
        <a href="/reminders/new" class="btn-cozy btn-cozy-primary">Add your first reminder</a>
      </div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2 : Restyle `partials/reminder_card.html`**

```html
<div id="reminder-card-{{ r.id }}"
     class="border-t border-white/10 pt-4 first:border-t-0 first:pt-0">
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-3">
      {% if r.icon %}<span class="text-2xl">{{ r.icon }}</span>{% endif %}
      <h2 class="display-2">{{ r.name }}</h2>
    </div>
    {% if r.tracked and progress.goal %}
      <span class="text-sm" style="color: var(--text-secondary)">
        {{ progress.count }} / {{ progress.goal }}
      </span>
    {% endif %}
  </div>

  {% if r.tracked and progress.goal %}
    <div class="progress-track mb-3">
      <div class="progress-fill" style="width: {{ [progress.percent or 0, 100]|min }}%"></div>
    </div>
  {% endif %}

  <div class="flex gap-2 mt-3">
    {% if r.tracked %}
      <button
        hx-post="/api/events"
        hx-vals='{"reminder_id": {{ r.id }}, "kind": "ack"}'
        hx-target="#reminder-card-{{ r.id }}"
        hx-swap="outerHTML"
        onclick="this.classList.add('splashing'); setTimeout(() => this.classList.remove('splashing'), 600)"
        class="btn-cozy btn-cozy-primary">
        +1 {{ r.unit_label or 'done' }}
      </button>
    {% endif %}
  </div>
</div>
```

- [ ] **Step 3 : Smoke test**

```bash
pytest -v
```

All 84 still pass (templates only changed cosmetically).

- [ ] **Step 4 : Commit**

```bash
git add courant/templates/dashboard.html courant/templates/partials/reminder_card.html
git commit -m "feat(ui): cozy glassmorphism panel layout for dashboard"
```

---

## Task 4 : Glassmorphism panels for /reminders, /stats, /settings

**Files:**
- Modify: `courant/templates/reminders.html`
- Modify: `courant/templates/stats.html`
- Modify: `courant/templates/settings.html`
- Modify: `courant/templates/partials/reminder_row.html`

- [ ] **Step 1 : Restyle `reminders.html`**

```html
{% extends "base.html" %}

{% block title %}Reminders — Courant{% endblock %}

{% block content %}
<div class="flex justify-center pt-12">
  <div class="panel panel-wide w-full">
    <div class="flex items-center justify-between mb-6">
      <h1 class="display-1">Reminders</h1>
      <a href="/reminders/new" class="btn-cozy btn-cozy-primary">+ New reminder</a>
    </div>

    {% if reminders %}
      <div class="divide-y divide-white/10">
        {% for r in reminders %}
          {% include "partials/reminder_row.html" %}
        {% endfor %}
      </div>
    {% else %}
      <p style="color: var(--text-secondary)" class="text-center py-8">
        No reminders yet. Click "New reminder" to add one.
      </p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2 : Restyle `partials/reminder_row.html`**

```html
<div id="reminder-row-{{ r.id }}" class="flex items-center justify-between py-4">
  <div class="flex items-center gap-3">
    {% if r.icon %}<span class="text-xl">{{ r.icon }}</span>{% endif %}
    <div>
      <div class="font-medium">{{ r.name }}</div>
      <div class="text-sm" style="color: var(--text-muted)">
        Every {{ r.interval_minutes }} min
        {% if r.tracked %} · tracked ({{ r.daily_goal }}/day){% endif %}
        {% if not r.enabled %} · <span style="color: #fbbf24">disabled</span>{% endif %}
      </div>
    </div>
  </div>
  <div class="flex items-center gap-3">
    <a href="/reminders/{{ r.id }}/edit" class="text-sm" style="color: var(--accent-blue)">Edit</a>
    <button
      hx-post="/reminders/{{ r.id }}/toggle"
      hx-target="#reminder-row-{{ r.id }}"
      hx-swap="outerHTML"
      class="text-sm" style="color: {{ '#fbbf24' if r.enabled else '#34d399' }}">
      {{ 'Disable' if r.enabled else 'Enable' }}
    </button>
    <form method="post" action="/reminders/{{ r.id }}/delete" class="inline">
      <button type="submit" class="text-sm" style="color: #f87171"
              onclick="return confirm('Delete &quot;{{ r.name }}&quot; and all its events ?')">
        Delete
      </button>
    </form>
  </div>
</div>
```

- [ ] **Step 3 : Restyle `stats.html`**

```html
{% extends "base.html" %}

{% block title %}Stats — Courant{% endblock %}

{% block content %}
<div class="flex justify-center pt-12">
  <div class="panel panel-narrow w-full">
    <h1 class="display-1 mb-6">Today's stats</h1>

    {% if reminders %}
      <div class="space-y-4">
        {% for r in reminders %}
          {% set progress = progresses[r.id] %}
          <div class="flex items-center justify-between border-t border-white/10 pt-4 first:border-t-0 first:pt-0">
            <div class="flex items-center gap-3">
              {% if r.icon %}<span class="text-xl">{{ r.icon }}</span>{% endif %}
              <span class="font-medium">{{ r.name }}</span>
            </div>
            <div class="text-right">
              <div class="display-2">
                {{ progress.count }}{% if progress.goal %} / {{ progress.goal }}{% endif %}
              </div>
              {% if progress.percent is not none %}
                <div class="text-sm" style="color: var(--text-muted)">{{ "%.0f"|format(progress.percent) }}%</div>
              {% else %}
                <div class="text-sm" style="color: var(--text-muted)">not tracked</div>
              {% endif %}
            </div>
          </div>
        {% endfor %}
      </div>
      <p class="text-sm mt-6" style="color: var(--text-muted)">
        Weekly/monthly aggregates coming later.
      </p>
    {% else %}
      <p style="color: var(--text-secondary)" class="text-center py-8">
        No reminders configured.
      </p>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4 : Restyle `settings.html`** (adds scene selector — Task 7 wires it)

```html
{% extends "base.html" %}

{% block title %}Settings — Courant{% endblock %}

{% block content %}
<div class="flex justify-center pt-12">
  <div class="panel panel-narrow w-full">
    <h1 class="display-1 mb-6">Settings</h1>

    <form method="post" action="/settings" class="space-y-4">
      <div>
        <label class="block mb-1">Snooze duration (minutes)</label>
        <input name="snooze_minutes" type="number" min="1" required value="{{ snooze_minutes }}">
        <p class="text-xs mt-1" style="color: var(--text-muted)">
          How long to delay a reminder when you click "Snooze" on a notification.
        </p>
      </div>

      <div>
        <label class="block mb-1">Ambient scene</label>
        <select name="current_scene"
                class="w-full px-3 py-2 rounded-lg"
                style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: var(--text-primary)">
          {% for scene_name in available_scenes %}
            <option value="{{ scene_name }}" {% if scene_name == current_scene %}selected{% endif %}>
              {{ scene_name|replace('-', ' ')|title }}
            </option>
          {% endfor %}
        </select>
      </div>

      <div class="pt-4 border-t border-white/10">
        <button type="submit" class="btn-cozy btn-cozy-primary">Save</button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5 : Smoke test**

```bash
pytest -v
```

All 84 still pass.

- [ ] **Step 6 : Commit**

```bash
git add courant/templates/
git commit -m "feat(ui): cozy panels for /reminders, /stats, /settings"
```

---

## Task 5 : Restyle the reminder form (new + edit)

**Files:**
- Modify: `courant/templates/reminder_form.html`

- [ ] **Step 1 : Replace the form template**

```html
{% extends "base.html" %}

{% block title %}{{ 'New' if is_new else 'Edit' }} reminder — Courant{% endblock %}

{% block content %}
<div class="flex justify-center pt-12">
  <div class="panel panel-wide w-full">
    <h1 class="display-1 mb-6">{{ 'New' if is_new else 'Edit' }} reminder</h1>

    <form method="post"
          action="{{ '/reminders' if is_new else '/reminders/' ~ reminder.id }}"
          class="space-y-5">

      <div>
        <label class="block mb-1">Name</label>
        <input name="name" type="text" required value="{{ reminder.name if reminder else '' }}">
      </div>

      <div>
        <label class="block mb-1">Message</label>
        <input name="message" type="text" required value="{{ reminder.message if reminder else '' }}">
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block mb-1">Icon (emoji)</label>
          <input name="icon" type="text" maxlength="4" value="{{ reminder.icon if reminder else '' }}">
        </div>
        <div>
          <label class="block mb-1">Every X minutes</label>
          <input name="interval_minutes" type="number" min="1" required
                 value="{{ reminder.interval_minutes if reminder else 45 }}">
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block mb-1">Active from</label>
          <input name="active_hours_start" type="time" required
                 value="{{ '%02d:%02d'|format(reminder.active_hours[0].hour, reminder.active_hours[0].minute) if reminder else '09:00' }}">
        </div>
        <div>
          <label class="block mb-1">Active until</label>
          <input name="active_hours_end" type="time" required
                 value="{{ '%02d:%02d'|format(reminder.active_hours[1].hour, reminder.active_hours[1].minute) if reminder else '18:00' }}">
        </div>
      </div>

      <div>
        <label class="block mb-1">Active days (comma-separated)</label>
        <input name="active_days" type="text" value="{{ active_days_csv }}">
        <p class="text-xs mt-1" style="color: var(--text-muted)">
          Use abbreviations : mon, tue, wed, thu, fri, sat, sun
        </p>
      </div>

      <div class="border-t border-white/10 pt-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" name="tracked" value="on"
                 {% if reminder and reminder.tracked %}checked{% endif %}>
          <span>Track progress toward a daily goal</span>
        </label>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block mb-1">Unit label</label>
          <input name="unit_label" type="text" placeholder="glass, cup..."
                 value="{{ reminder.unit_label if reminder and reminder.unit_label else '' }}">
        </div>
        <div>
          <label class="block mb-1">Unit amount</label>
          <input name="unit_amount" type="number" min="1" placeholder="250"
                 value="{{ reminder.unit_amount if reminder and reminder.unit_amount else '' }}">
        </div>
        <div>
          <label class="block mb-1">Daily goal</label>
          <input name="daily_goal" type="number" min="1" placeholder="8"
                 value="{{ reminder.daily_goal if reminder and reminder.daily_goal else '' }}">
        </div>
      </div>

      <div class="flex gap-3 pt-4 border-t border-white/10">
        <button type="submit" class="btn-cozy btn-cozy-primary">
          {{ 'Create' if is_new else 'Save' }}
        </button>
        <a href="/reminders" class="btn-cozy">Cancel</a>
      </div>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2 : Smoke test**

```bash
pytest -v
```

All 84 still pass.

- [ ] **Step 3 : Commit**

```bash
git add courant/templates/reminder_form.html
git commit -m "feat(ui): cozy reminder form (new + edit)"
```

---

## Task 6 : First scene — ocean-depth (validates the framework)

**Files:**
- Create: `courant/static/scenes/ocean-depth.js`

This is the first scene. If it works visually, the framework is validated and the other 4 scenes follow the same pattern.

- [ ] **Step 1 : Create `courant/static/scenes/ocean-depth.js`**

```javascript
// Ocean depth — bubbles rising slowly through a blue gradient with diagonal light rays.

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    // Pre-allocate bubbles
    const BUBBLE_COUNT = 80;
    const bubbles = Array.from({ length: BUBBLE_COUNT }, () => spawnBubble(H()));

    let raf = null;
    let lastFrame = 0;
    const TARGET_FPS = 30;
    const FRAME_INTERVAL = 1000 / TARGET_FPS;

    function spawnBubble(maxY) {
      return {
        x: Math.random() * W(),
        y: maxY + Math.random() * 100,
        r: 1 + Math.random() * 4,
        vy: 0.3 + Math.random() * 0.6,
        alpha: 0.15 + Math.random() * 0.25,
        drift: (Math.random() - 0.5) * 0.3,
      };
    }

    function draw() {
      const w = W(), h = H();

      // Background gradient : deep navy → mid blue
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, '#0a2540');
      grad.addColorStop(1, '#1e5780');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Diagonal light rays (subtle)
      ctx.save();
      ctx.globalAlpha = 0.06;
      ctx.fillStyle = '#ffffff';
      for (let i = 0; i < 4; i++) {
        const offset = (i / 4) * w;
        ctx.beginPath();
        ctx.moveTo(offset, 0);
        ctx.lineTo(offset + 200, 0);
        ctx.lineTo(offset + 400 + (i * 50), h);
        ctx.lineTo(offset + 200 + (i * 50), h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      // Bubbles
      for (const b of bubbles) {
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${b.alpha})`;
        ctx.fill();

        b.y -= b.vy;
        b.x += b.drift;
        if (b.y < -10) {
          Object.assign(b, spawnBubble(h));
          b.y = h + 10;
        }
      }
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) {
        draw();
        lastFrame = now;
      }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return function cleanup() {
      if (raf) cancelAnimationFrame(raf);
    };
  },
};
```

- [ ] **Step 2 : Manual visual smoke test (developer responsibility)**

```bash
source .venv/bin/activate
courant start
```

Open `http://localhost:8765` in a browser. Expected :
- Background is a deep blue gradient with small white bubbles rising slowly
- A glassmorphism panel is centered with "Today" title
- The reminder cards are styled with the new cozy aesthetic
- The bubbles continue to rise smoothly at ~30fps
- No console errors in the browser devtools

If anything looks off, fix the scene or CSS before committing.

- [ ] **Step 3 : Commit**

```bash
git add courant/static/scenes/ocean-depth.js
git commit -m "feat(scene): ocean-depth — rising bubbles in blue gradient"
```

---

## Task 7 : Scene selector + persistence

**Files:**
- Modify: `courant/web.py` (settings page accepts `current_scene` form field)

- [ ] **Step 1 : Update settings handler in `web.py`**

The settings handler currently takes only `snooze_minutes`. Extend it :

```python
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
```

At the top of `web.py`, declare the available scenes list :

```python
AVAILABLE_SCENES = ("ocean-depth", "rainy-window", "sunset-beach", "forest-stream", "calm-night")
```

(Only `ocean-depth` exists as a real module at this point ; the other names won't load until Tasks 10-13. That's intentional — listing them in settings now means the dropdown is complete the moment new scenes ship.)

- [ ] **Step 2 : Update settings test in `tests/test_web.py`**

Find `test_settings_post_updates_value` and update the POST data to include `current_scene` :

```python
async def test_settings_post_updates_value(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/settings",
            data={"snooze_minutes": "15", "current_scene": "ocean-depth"},
            follow_redirects=False,
        )
    assert resp.status_code in (302, 303)
    from courant.repository import get_setting
    assert get_setting(memory_db, "snooze_minutes") == "15"
    assert get_setting(memory_db, "current_scene") == "ocean-depth"


async def test_settings_post_rejects_unknown_scene(memory_db: sqlite3.Connection):
    migrate(memory_db)
    service = ReminderService(memory_db)
    app = create_app(service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/settings",
            data={"snooze_minutes": "10", "current_scene": "non-existent-scene"},
        )
    assert resp.status_code == 400
```

- [ ] **Step 3 : Run tests**

```bash
pytest -v
```

Expect : 85 passing (84 + 1 new scene rejection test).

- [ ] **Step 4 : Manual verification**

Visit `/settings`, pick a scene from the dropdown, save. The page should redirect and the selection should persist.

Visit `/` — the scene loader should respect the new choice (read from `body.dataset.scene`).

- [ ] **Step 5 : Commit**

```bash
git add courant/web.py tests/test_web.py
git commit -m "feat(settings): persist ambient scene choice"
```

---

## Tasks 8 + 9 : Splash animation polish + scene helpers

**Files:**
- Modify: `courant/static/scene-loader.js` (extract a particle helper module since all scenes use particles)
- Create: `courant/static/scenes/_helpers.js` (shared utilities)

- [ ] **Step 1 : Create `courant/static/scenes/_helpers.js`**

```javascript
// Shared helpers for scenes. Import as :
//   import { Particles, gradient } from './_helpers.js';

export function gradient(ctx, w, h, stops) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  for (const [pos, color] of stops) g.addColorStop(pos, color);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

export class Particles {
  constructor(count, spawnFn) {
    this.spawn = spawnFn;
    this.items = Array.from({ length: count }, () => spawnFn());
  }

  update(updateFn, respawnPredicate) {
    for (const p of this.items) {
      updateFn(p);
      if (respawnPredicate(p)) Object.assign(p, this.spawn());
    }
  }

  draw(drawFn, ctx) {
    for (const p of this.items) drawFn(ctx, p);
  }
}
```

- [ ] **Step 2 : Refactor `ocean-depth.js` to use the helpers**

```javascript
import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const bubbles = new Particles(80, () => ({
      x: Math.random() * W(),
      y: H() + Math.random() * 100,
      r: 1 + Math.random() * 4,
      vy: 0.3 + Math.random() * 0.6,
      alpha: 0.15 + Math.random() * 0.25,
      drift: (Math.random() - 0.5) * 0.3,
    }));

    let raf = null;
    let lastFrame = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();
      gradient(ctx, w, h, [[0, '#0a2540'], [1, '#1e5780']]);

      // Diagonal light rays
      ctx.save();
      ctx.globalAlpha = 0.06;
      ctx.fillStyle = '#ffffff';
      for (let i = 0; i < 4; i++) {
        const x = (i / 4) * w;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + 200, 0);
        ctx.lineTo(x + 400 + (i * 50), h);
        ctx.lineTo(x + 200 + (i * 50), h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      bubbles.update(
        (b) => { b.y -= b.vy; b.x += b.drift; },
        (b) => b.y < -10,
      );
      bubbles.draw((ctx, b) => {
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${b.alpha})`;
        ctx.fill();
      }, ctx);
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
```

- [ ] **Step 3 : Visual smoke check** (should look identical to Task 6)

```bash
courant start
```

Visit `/` — ocean-depth still renders correctly.

- [ ] **Step 4 : Commit**

```bash
git add courant/static/scenes/
git commit -m "refactor(scenes): extract Particles + gradient helpers"
```

---

## Task 10 : Scene — rainy-window

**Files:**
- Create: `courant/static/scenes/rainy-window.js`

- [ ] **Step 1 : Create the scene**

```javascript
import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const drops = new Particles(150, () => ({
      x: Math.random() * W(),
      y: -10 - Math.random() * H(),
      length: 8 + Math.random() * 20,
      speed: 6 + Math.random() * 8,
      alpha: 0.2 + Math.random() * 0.3,
      // Each drop has a trailing streak (the ruissellement effect)
      streak: 30 + Math.random() * 50,
    }));

    let raf = null;
    let lastFrame = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();

      // Dark gray-blue sky
      gradient(ctx, w, h, [[0, '#1a2332'], [1, '#3d556e']]);

      // Warm interior light glow in bottom-right corner
      const glow = ctx.createRadialGradient(w * 0.85, h * 0.9, 0, w * 0.85, h * 0.9, 400);
      glow.addColorStop(0, 'rgba(232, 213, 168, 0.25)');
      glow.addColorStop(1, 'rgba(232, 213, 168, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // Rain streaks
      ctx.lineWidth = 1;
      drops.draw((ctx, d) => {
        ctx.strokeStyle = `rgba(200, 220, 240, ${d.alpha})`;
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x - d.length * 0.2, d.y + d.length);
        ctx.stroke();
      }, ctx);

      drops.update(
        (d) => { d.y += d.speed; d.x -= d.speed * 0.2; },
        (d) => d.y > h + 20,
      );
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
```

- [ ] **Step 2 : Visual smoke**

Set scene to rainy-window via `/settings`, visit `/`. Should see diagonal rain streaks falling on a gray-blue background with a warm glow in the bottom-right.

- [ ] **Step 3 : Commit**

```bash
git add courant/static/scenes/rainy-window.js
git commit -m "feat(scene): rainy-window — diagonal rain on gray-blue sky"
```

---

## Task 11 : Scene — sunset-beach (light theme)

**Files:**
- Create: `courant/static/scenes/sunset-beach.js`

- [ ] **Step 1 : Create the scene**

```javascript
import { gradient } from './_helpers.js';

export default {
  theme: 'light',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    let raf = null;
    let lastFrame = 0;
    let t = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();

      // Vertical gradient : orange → pink → violet
      gradient(ctx, w, h, [
        [0,    '#fdb585'],
        [0.4,  '#e89bb0'],
        [0.7,  '#c66a8e'],
        [1,    '#5c4a7a'],
      ]);

      // Sun — large soft circle near horizon
      const sunY = h * 0.7;
      const sunGrad = ctx.createRadialGradient(w / 2, sunY, 0, w / 2, sunY, 120);
      sunGrad.addColorStop(0, 'rgba(255, 230, 200, 0.9)');
      sunGrad.addColorStop(1, 'rgba(255, 200, 150, 0)');
      ctx.fillStyle = sunGrad;
      ctx.fillRect(0, 0, w, h);

      // Sea : darker band in lower third
      ctx.fillStyle = 'rgba(40, 30, 70, 0.4)';
      ctx.fillRect(0, h * 0.75, w, h * 0.25);

      // Animated waves (sine lines)
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.lineWidth = 1.5;
      for (let layer = 0; layer < 4; layer++) {
        ctx.beginPath();
        const baseY = h * 0.78 + layer * 12;
        for (let x = 0; x <= w; x += 6) {
          const y = baseY + Math.sin((x + t * (1 + layer * 0.2)) * 0.015 + layer) * 6;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      t += 1;
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
```

- [ ] **Step 2 : Visual smoke**

Switch scene to `sunset-beach`, verify : warm gradient, sun glow, animated waves at bottom, panel uses the dark-glass variant for contrast.

- [ ] **Step 3 : Commit**

```bash
git add courant/static/scenes/sunset-beach.js
git commit -m "feat(scene): sunset-beach — orange-violet gradient with animated waves"
```

---

## Task 12 : Scene — forest-stream

**Files:**
- Create: `courant/static/scenes/forest-stream.js`

- [ ] **Step 1 : Create the scene**

```javascript
import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const leaves = new Particles(40, () => ({
      x: Math.random() * W(),
      y: -10,
      vy: 0.3 + Math.random() * 0.5,
      vx: (Math.random() - 0.5) * 0.4,
      rot: Math.random() * Math.PI * 2,
      vrot: (Math.random() - 0.5) * 0.05,
      size: 5 + Math.random() * 6,
      color: ['#c4945c', '#b8702f', '#9d5e1f', '#e8b569'][Math.floor(Math.random() * 4)],
    }));

    let raf = null;
    let lastFrame = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();

      // Green forest gradient
      gradient(ctx, w, h, [[0, '#2d3e2f'], [1, '#5a7a5d']]);

      // Vertical god-rays (subtle)
      ctx.save();
      ctx.globalAlpha = 0.05;
      ctx.fillStyle = '#e8d090';
      for (let i = 0; i < 3; i++) {
        const x = (i / 3 + 0.15) * w;
        ctx.beginPath();
        ctx.moveTo(x - 40, 0);
        ctx.lineTo(x + 40, 0);
        ctx.lineTo(x + 100, h);
        ctx.lineTo(x - 100, h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      // Leaves
      leaves.draw((ctx, l) => {
        ctx.save();
        ctx.translate(l.x, l.y);
        ctx.rotate(l.rot);
        ctx.fillStyle = l.color;
        ctx.globalAlpha = 0.85;
        ctx.beginPath();
        ctx.ellipse(0, 0, l.size, l.size * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }, ctx);

      leaves.update(
        (l) => { l.y += l.vy; l.x += l.vx; l.rot += l.vrot; },
        (l) => l.y > h + 20,
      );
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
```

- [ ] **Step 2 : Visual smoke + Commit**

```bash
git add courant/static/scenes/forest-stream.js
git commit -m "feat(scene): forest-stream — falling leaves through god-rays"
```

---

## Task 13 : Scene — calm-night

**Files:**
- Create: `courant/static/scenes/calm-night.js`

- [ ] **Step 1 : Create the scene**

```javascript
import { Particles, gradient } from './_helpers.js';

export default {
  theme: 'dark',

  init(canvas, ctx) {
    const W = () => window.innerWidth;
    const H = () => window.innerHeight;

    const stars = new Particles(200, () => ({
      x: Math.random() * W(),
      y: Math.random() * H() * 0.7,  // stars only in top 70%
      r: 0.5 + Math.random() * 1.5,
      baseAlpha: 0.3 + Math.random() * 0.5,
      twinkleSpeed: 0.001 + Math.random() * 0.003,
      phase: Math.random() * Math.PI * 2,
    }));

    let raf = null;
    let lastFrame = 0;
    let t = 0;
    const FRAME_INTERVAL = 1000 / 30;

    function draw() {
      const w = W(), h = H();
      gradient(ctx, w, h, [[0, '#0c1024'], [1, '#252a4a']]);

      // Moon — top-right
      const moonX = w * 0.85, moonY = h * 0.2;
      const moonGlow = ctx.createRadialGradient(moonX, moonY, 0, moonX, moonY, 90);
      moonGlow.addColorStop(0, 'rgba(255, 248, 217, 0.95)');
      moonGlow.addColorStop(0.3, 'rgba(255, 248, 217, 0.4)');
      moonGlow.addColorStop(1, 'rgba(255, 248, 217, 0)');
      ctx.fillStyle = moonGlow;
      ctx.beginPath();
      ctx.arc(moonX, moonY, 80, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#fff8d9';
      ctx.beginPath();
      ctx.arc(moonX, moonY, 35, 0, Math.PI * 2);
      ctx.fill();

      // Twinkling stars
      stars.draw((ctx, s) => {
        const alpha = s.baseAlpha + Math.sin(t * s.twinkleSpeed + s.phase) * 0.3;
        ctx.fillStyle = `rgba(255, 248, 217, ${Math.max(0, alpha)})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }, ctx);

      t += 16;  // approx 1 frame at 30fps = 33ms ; using 16 gives a slower twinkle
    }

    function loop(now) {
      if (now - lastFrame >= FRAME_INTERVAL) { draw(); lastFrame = now; }
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);

    return () => { if (raf) cancelAnimationFrame(raf); };
  },
};
```

- [ ] **Step 2 : Visual smoke + Commit**

```bash
git add courant/static/scenes/calm-night.js
git commit -m "feat(scene): calm-night — twinkling stars and moon glow"
```

---

## Task 14 : Polish — splash button animation already in place, verify it triggers

(The `splash` keyframe in `courant.css` and the `onclick` attribute in `reminder_card.html` were both set up in Tasks 1 + 3. This task is just verification.)

- [ ] **Step 1 : Visual smoke**

In the browser, click `+1 glass` on the dashboard. The button should briefly scale up to 115 % then back. The progress bar should animate to its new width over ~600 ms.

If either animation doesn't fire, investigate :
- Splash : check the `onclick` attribute is on the button (it adds the `splashing` class for 600 ms)
- Progress : check the `.progress-fill { transition: width 600ms }` CSS rule

- [ ] **Step 2 : Document**

No commit needed if everything works. If you make a fix, commit it.

---

## Task 15 : Add ADDING_A_SCENE.md contributor guide

**Files:**
- Create: `docs/ADDING_A_SCENE.md`

- [ ] **Step 1 : Create the guide**

```markdown
# Adding a new ambient scene to Courant

Each ambient scene is a single self-contained JavaScript file under
`courant/static/scenes/`. The framework calls a small contract on it,
nothing more. This is meant to be the most contributor-friendly entry
point in the codebase.

## The contract

Your scene file must `export default` an object with two members :

```javascript
export default {
  theme: 'dark',   // or 'light' — controls the glassmorphism panel contrast

  init(canvas, ctx) {
    // canvas : the DOM canvas element, already DPI-scaled
    // ctx    : the 2D rendering context

    // Set up your animation loop with requestAnimationFrame.
    // Return a cleanup function that cancels the loop.

    let raf = requestAnimationFrame(function loop() {
      // ... draw your frame here ...
      raf = requestAnimationFrame(loop);
    });

    return function cleanup() {
      cancelAnimationFrame(raf);
    };
  },
};
```

## Helpers

`courant/static/scenes/_helpers.js` exposes :

- `gradient(ctx, w, h, stops)` — draws a vertical gradient fill across the canvas
- `Particles` — a small particle pool (constructor takes count + spawn fn ; methods `update(updateFn, respawnPredicate)` and `draw(drawFn, ctx)`)

Import them as `import { Particles, gradient } from './_helpers.js';`.

## Performance

- Cap your loop at 30 fps for battery friendliness. The existing scenes use a `lastFrame` timestamp + `FRAME_INTERVAL` pattern — copy it.
- Avoid creating new objects in the inner loop. Use the `Particles` pool.
- The scene loader pauses your loop automatically when the tab is hidden.
- Respect `prefers-reduced-motion` : the global CSS rule already disables animations for those users, but if you do heavy work in `init` you should bail early.

## Registering the scene

Add the slug (the filename without `.js`) to two places :

1. `AVAILABLE_SCENES` in `courant/web.py` — gates the settings dropdown
2. Optionally `docs/superpowers/specs/2026-05-21-courant-design.md` — for the
   design palette reference table

## Style guidance

- Use a tight palette : 2-4 hex codes max. The existing scenes hold to this.
- Avoid pure white. `#f5f5f5` or warm whites (`#fff8d9`) feel cozier.
- Subtle motion beats showy motion. Bubbles drift, rain falls at an angle,
  stars twinkle slowly — none of this jumps or flashes.
- Test on both bright and dim screens. Glassmorphism contrast can be fragile.

## Submitting

Open a PR with :
- Your scene file
- A short description of the vibe you were going for
- A screenshot or short GIF if possible

We welcome variety. Different cultures, different times of day, different
weather, different planets — all good.
```

- [ ] **Step 2 : Commit**

```bash
git add docs/ADDING_A_SCENE.md
git commit -m "docs: contributor guide for adding ambient scenes"
```

---

## Task 16 : README updates + screenshots note

**Files:**
- Modify: `README.md`

- [ ] **Step 1 : Update Status section**

```markdown
## Status

- ✅ Phase 1 — Core CLI + desktop notifications working end-to-end
- ✅ Phase 2 — Functional web UI (FastAPI + HTMX)
- ✅ Phase 3 — Cozy aesthetic with ambient scenes (ocean, rain, sunset, forest, night)
- ⏳ Phase 4 — Polish, systemd integration, ambient audio, PyPI release
```

- [ ] **Step 2 : Add a "Scenes" mini-section**

After the Usage section, add :

```markdown
## Scenes

Courant ships with 5 ambient scenes you can choose from in Settings :

| Scene | Vibe |
|---|---|
| Ocean depth | Bubbles rising through a deep-blue gradient |
| Rainy window | Diagonal rain streaks on a gray-blue sky with a warm glow indoors |
| Sunset beach | Orange-violet sky with animated waves |
| Forest stream | Autumn leaves falling through green god-rays |
| Calm night | Twinkling stars and a moon glow |

Want to add your own ? See [`docs/ADDING_A_SCENE.md`](docs/ADDING_A_SCENE.md).
```

- [ ] **Step 3 : Commit and tag**

```bash
git add README.md
git commit -m "docs: mark Phase 3 complete and document scenes"
git tag -a phase-3-complete -m "Phase 3: Cozy aesthetic with 5 ambient scenes"
```

---

## Task 17 : Final lint/type/test pass + manual sweep

- [ ] **Step 1 : Run the full pipeline**

```bash
source .venv/bin/activate
ruff check courant tests
mypy courant
pytest -v
```

All green expected (no Python code changed structurally ; only templates and static assets).

- [ ] **Step 2 : Browser sweep**

Open the daemon (`courant start`) and visit each page :

- `/` — dashboard renders with the cozy panel
- `/reminders` — list page works, edit/disable/delete still function
- `/reminders/new` — form looks cozy, submitting still creates
- `/stats` — stats panel
- `/settings` — snooze + scene picker, all 5 scenes selectable

Try each scene in turn from settings. Verify :
- Crossfade between scenes
- Panel readability on both dark and light themes (sunset-beach is the light one)
- No browser console errors
- Animation smooth (~30 fps)
- Tab hidden → animation pauses (toggle DevTools to background the tab)

- [ ] **Step 3 : Open PR and verify CI**

```bash
git push origin phase-3-aesthetic
git push origin phase-3-complete
gh pr create --base main --head phase-3-aesthetic \
  --title "Phase 3 : Cozy aesthetic with ambient scenes" \
  --body "Transforms the bare-Tailwind Phase 2 UI into the cozy lo-fi aesthetic from the original design : glassmorphism panel, Fraunces+Inter typography, and 5 ambient scenes (ocean-depth, rainy-window, sunset-beach, forest-stream, calm-night). Each scene is a self-contained JS module loaded dynamically. The audio player and PyPI publish are deferred to Phase 4."
```

Watch the CI checks pass, then merge :

```bash
gh pr merge --merge --delete-branch=false
gh release create phase-3-complete \
  --title "Phase 3 — Cozy Aesthetic" \
  --notes "Adds the signature visual layer : 5 ambient scenes (ocean, rain, sunset, forest, night), glassmorphism panel, custom typography. Each scene is a self-contained JS module so contributors can add new ones via a single file (see docs/ADDING_A_SCENE.md)."
```

---

## Phase 3 Done ✓

Courant now matches the design spec's cozy lo-fi aesthetic. The web UI is no longer just functional — it's something you want to open.

**Tests :** ~85 still pass (no backend changes ; we added 1 scene-rejection test).

**Next phase :** Phase 4 — systemd integration (`courant install` creates the user service), ambient audio player, PyPI publish, optional CODE_OF_CONDUCT.md and issue templates.
