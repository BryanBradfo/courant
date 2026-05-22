# Installing Courant

## End users

The easiest path — `pipx` installs Courant in an isolated venv :

```bash
pipx install courant
courant install-scenes        # ~10 MB of ambient videos
courant install-audio         # ~2 MB of ambient sounds (optional)
courant install               # creates a systemd user service (auto-starts at login)
```

That's it. The web UI is at <http://localhost:8765>.

## Development install

```bash
git clone https://github.com/BryanBradfo/courant
cd courant
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
courant install-scenes
courant start    # foreground daemon
```

## Maintainer notes — PyPI publishing

The `publish.yml` workflow publishes via OIDC trusted publishing — no API token required.

One-time setup :

1. Go to <https://pypi.org/manage/account/publishing/> and add a "Pending Publisher" :
   - PyPI Project Name : `courant`
   - Owner : `BryanBradfo`
   - Repository name : `courant`
   - Workflow name : `publish.yml`
   - Environment name : `pypi`

2. Create the GitHub environment named `pypi` in the repo settings.

3. Tag the release : `git tag v0.1.0 && git push origin v0.1.0`. The workflow builds + publishes automatically.
