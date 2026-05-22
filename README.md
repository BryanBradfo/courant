# Courant

> Un rappel cozy pour les devs : eau, yeux, étirements.

Linux desktop app that sends customizable notifications to remind you to drink water, rest your eyes, stretch — with a cozy lo-fi web interface (coming in Phase 2).

**Status:**
- ✅ Phase 1 (Core CLI + notifications) — done
- ⏳ Phase 2 (Web UI) — next
- ⏳ Phase 3 (Cozy aesthetic, scenes)
- ⏳ Phase 4 (Polish, systemd, PyPI)

## Quick start (dev)

    git clone https://github.com/<user>/courant
    cd courant
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"

    courant start                    # foreground daemon
    courant status                   # in another terminal: see reminders
    # Ctrl+C in the daemon terminal to stop

On first launch, three default reminders are seeded: water (45 min, tracked, 8 verres/day), eye breaks (20 min), stretching (90 min).

## Tests

    pytest -v

## License

MIT
