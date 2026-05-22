# Contributing to Courant

First off : thank you for considering a contribution. Courant exists because developers, scientists, and other knowledge workers care about not burning out — your help keeps the project moving toward that goal.

## What we're looking for

Contributions, roughly in order of "thank you, please do" :

1. **Bug reports and compatibility fixes** — especially from non-GNOME desktops (KDE Plasma, XFCE, Hyprland, Cosmic, sway, i3). Include your distro, desktop environment, `courant version`, and the relevant lines from `~/.cache/courant/logs/courant.log`. A failing test that reproduces the bug is gold.
2. **Translations** — Courant is English-first but originated in French ; the design docs in `docs/` are still in French and would benefit from translation. Phase 5 will add a proper `i18n` layer ; for now, a `README.<lang>.md` and a translated `courant/data/default_reminders.<lang>.json` are useful drops.
3. **New ambient scenes for Phase 3** — once Phase 3 lands, each scene is a self-contained CSS + Canvas module (`courant/static/scenes/<name>.{js,css}`). "Add your favorite scene" is meant to be the easiest first contribution. A guide will live at `docs/ADDING_A_SCENE.md` once Phase 3 establishes the pattern. Until then, scene proposals (sketches, palettes, references) in issues are very welcome.
4. **Tests for edge cases** the existing suite misses : overnight `active_hours` (start > end), disabled reminder paths, snooze chains, DST transitions.
5. **Documentation** : per-distro install recipes, screenshots, animated GIF demos, blog post writeups.

Harder to land :

- **Feature creep beyond "cozy local reminder daemon"**. Slack/Discord/Telegram bridges, calendar sync, time-tracking, AI-generated reminders, mobile companion apps — these are interesting products on their own, but not Courant. Phase 4 will expose a small webhook surface so external tools can listen ; please build separate projects around that rather than into the core. Open an issue first if you're unsure.
- **Architectural changes** to the layered design (`repository → service → cli/web`, see [design spec](docs/superpowers/specs/2026-05-21-courant-design.md)) without a discussion in an issue. The boundaries exist for testability — rewriting them invalidates the spec.
- **AI-generated PRs without ownership.** Courant was largely built with Claude, so we are *not* anti-AI. But the author must (a) actually run `pytest -v`, `ruff check`, and `mypy courant` locally before pushing ; (b) be able to defend the design choices in review ; (c) own any follow-up bug reports for several weeks after merge. "Claude wrote this, I didn't read it" is an instant close.

When you're unsure if a contribution fits, **open an issue first**. A 10-line "is this welcome ?" thread saves us both hours of disagreement at PR review time.

## Development setup

```bash
git clone git@github.com:BryanBradfo/courant.git
cd courant
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run the daemon manually with `courant start`. Check the database state with `courant status`. Stop with `Ctrl+C` (or `courant stop` once Phase 4 ships systemd integration).

Data lives at standard XDG paths :

- Config : `~/.config/courant/` (none yet — Phase 2)
- Database : `~/.local/share/courant/courant.db`
- Logs : `~/.cache/courant/logs/courant.log`

## Coding standards

We use three tools, all configured in `pyproject.toml` :

- **Ruff** for lint + import sorting : `ruff check courant tests`
- **Mypy** in strict mode : `mypy courant`
- **Pytest** for tests : `pytest -v`

The CI pipeline (`.github/workflows/ci.yml`) runs all three on every push and PR across Python 3.11, 3.12, 3.13. Get them green locally before opening a PR.

### Architectural conventions

We follow strict layering (see [`docs/superpowers/specs/2026-05-21-courant-design.md`](docs/superpowers/specs/2026-05-21-courant-design.md) for the full picture) :

- `courant/repository.py` is the **only** module that performs SQL operations
- `courant/service.py` holds business logic and orchestrates everything
- `courant/notifier.py` knows nothing about reminders — just `(title, body, actions)`
- `courant/scheduler.py` consumes `service` + `notifier`, knows nothing about HTTP
- `courant/cli.py` wires everything at startup

When in doubt, check existing tests for the layer you're touching — they usually demonstrate the intended boundaries.

### Test-driven development

Phase 1 was built strictly TDD : a failing test before any new function, then the implementation. We don't enforce this for every PR, but tests are required for any new behavior. Bug fixes should include a regression test that fails on the old code.

## Pull request process

1. **Fork** the repo and create a feature branch from `main` : `git checkout -b feat/your-thing`
2. **Make focused commits**. Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`) are appreciated but not strictly required.
3. **Write or update tests** that cover your change.
4. **Run the full local pipeline** before pushing :
   ```
   ruff check courant tests && mypy courant && pytest -v
   ```
5. **Open the PR** against `main`. The CI runs automatically.
6. **Wait for review**. Solo project for now, so expect some delay during busy weeks. You can ping in the PR after a week of silence.

## Reporting bugs

Open an issue with :

- What you tried to do (reminder created with what config, action you took)
- What happened (full log output if available — log file is `~/.cache/courant/logs/courant.log`)
- What you expected
- Your environment : Linux distro, desktop environment, Python version, `courant version`

A minimal reproduction case is gold but not always required for obvious bugs.

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Be respectful, assume good faith, and prefer working on the project to working on each other.

## License

By contributing, you agree your code is released under the [MIT License](LICENSE).
