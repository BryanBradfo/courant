# Courant

[![CI](https://github.com/BryanBradfo/courant/actions/workflows/ci.yml/badge.svg)](https://github.com/BryanBradfo/courant/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)

> A cozy reminder for developers — drink water, rest your eyes, stretch.

Linux desktop app that fires customizable system notifications, tracks your daily progress, and serves a small web UI on `localhost:8765` for CRUD and stats. The UI features a full-screen ambient scene (ocean depth, rain, sunset, forest, or night sky) with a glassmorphism panel on top. The product name "Courant" means *current* / *flow* in French — the gentle stream that nudges you toward healthier breaks.

## Status

- ✅ Phase 1 — Core CLI + desktop notifications working end-to-end
- ✅ Phase 2 — Functional web UI (FastAPI + HTMX)
- ✅ Phase 3 — Cozy aesthetic with ambient scenes (ocean, rain, sunset, forest, night)
- ⏳ Phase 4 — Polish, systemd integration, ambient audio, PyPI release

## Quick start (dev)

```bash
git clone https://github.com/BryanBradfo/courant
cd courant
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

courant start    # foreground daemon
courant status   # (in another terminal) see configured reminders
# Ctrl+C in the daemon terminal to stop
```

On first launch, three default reminders are seeded:

| Reminder | Interval | Tracking |
|---|---|---|
| Drink water | 45 min | Yes (8 glasses/day goal) |
| Eye break (20-20-20) | 20 min | No |
| Stretch | 90 min | No |

All reminders fire only between 09:00–18:00 on weekdays by default. You can customize all of this from the web UI at <http://localhost:8765/reminders> while the daemon is running, or directly in the SQLite database at `~/.local/share/courant/courant.db`.

## Installing the ambient scenes

Courant uses 6 looping background videos (~110 MB total) for the cozy aesthetic. They are not bundled in the repo — fetch them with :

    courant install-scenes

Progress is shown per scene. Files land in `~/.local/share/courant/videos/`. If some downloads fail, re-run the command — it skips already-installed scenes.

Until you install them, you'll see a fallback gradient background.

## Usage

After `courant start`, point your browser at <http://localhost:8765> :

- **Dashboard** — see each reminder's daily progress and click `+1` to log a hit
- **Reminders** — create / edit / disable / delete reminders
- **Stats** — daily progress per reminder
- **Settings** — global preferences (e.g. snooze duration)

Notifications fire on the desktop via D-Bus as configured. Clicking a notification action ("+1 glass" or "Snooze 10 min") records an event in the same database the web UI reads from — both views stay in sync.

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

## Tests

```bash
pytest -v
```

Currently 84 tests covering models, SQLite repository, business logic, scheduler integration, the FastAPI web UI, and CLI smoke tests (including a subprocess test that verifies the daemon actually serves HTTP).

## Roadmap

This is a phased build. See [`docs/superpowers/specs/`](docs/superpowers/specs/) for the design spec (currently in French, English translation welcome) and [`docs/superpowers/plans/`](docs/superpowers/plans/) for phase-by-phase implementation plans.

Contributions are welcome — especially:

- **Translations** of user-facing strings and design docs
- **New ambient scenes** (each scene is a self-contained Canvas module — see [`docs/ADDING_A_SCENE.md`](docs/ADDING_A_SCENE.md))
- **Bug reports** from running on non-GNOME desktops (Plasma, XFCE, Hyprland…)

## License

MIT — see [LICENSE](LICENSE).
