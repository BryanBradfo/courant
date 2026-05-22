# Courant

[![CI](https://github.com/BryanBradfo/courant/actions/workflows/ci.yml/badge.svg)](https://github.com/BryanBradfo/courant/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)

> A cozy reminder for developers — drink water, rest your eyes, stretch.

Linux desktop app that fires customizable system notifications and tracks your daily progress, with a cozy lo-fi web interface (coming in Phase 2). The product name "Courant" means *current* / *flow* in French — the gentle stream that nudges you toward healthier breaks.

## Status

- ✅ Phase 1 — Core CLI + desktop notifications working end-to-end
- ⏳ Phase 2 — Web UI (FastAPI + HTMX)
- ⏳ Phase 3 — Cozy aesthetic with ambient scenes (rain, ocean, sunset…)
- ⏳ Phase 4 — Polish, systemd integration, PyPI release

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

All reminders fire only between 09:00–18:00 on weekdays by default. You can customize all of this directly in the SQLite database at `~/.local/share/courant/courant.db` until the web UI lands.

## Tests

```bash
pytest -v
```

Currently 64 tests covering models, SQLite repository, business logic, scheduler integration, and CLI smoke tests.

## Roadmap

This is a phased build. See [`docs/superpowers/specs/`](docs/superpowers/specs/) for the design spec (currently in French, English translation welcome) and [`docs/superpowers/plans/`](docs/superpowers/plans/) for phase-by-phase implementation plans.

Contributions are welcome — especially:

- **Translations** of user-facing strings and design docs
- **New ambient scenes** for Phase 3 (each scene is a small CSS + Canvas module — see `docs/ADDING_A_SCENE.md` when Phase 3 lands)
- **Bug reports** from running on non-GNOME desktops (Plasma, XFCE, Hyprland…)

## License

MIT — see [LICENSE](LICENSE).
