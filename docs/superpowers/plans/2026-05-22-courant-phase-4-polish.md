# Courant — Phase 4 (Polish, systemd, PyPI, Audio) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Courant installable for non-developers (`pipx install courant`), auto-starting at login (systemd user service), and with a delightful lo-fi audio companion. This is the last planned phase before "v1.0 done — community open" mode.

**Three sub-features:**

1. **systemd integration** — `courant install` generates and enables `~/.config/systemd/user/courant.service`. `courant uninstall` removes it cleanly.
2. **PyPI publish** — Package metadata polish, GitHub Actions release workflow on tag push, official release to PyPI.
3. **Audio player** — Floating bottom-right pill widget with play/pause + ambient track selector. 4 lo-fi tracks (rain, ocean waves, cafe, fireplace). Tracks hosted as `audio-v1` GitHub release.

**Tech additions:**
- `dataclasses_json` or stdlib `typing.TypedDict` for the audio registry — actually let's stick with the existing `dict[str, dict[str, str]]` pattern for consistency
- HTML5 `<audio>` element + small JS for play/pause UI

**Out of scope:**
- Mobile-responsive layout
- LAN access auth/login
- Webhook integrations
- Linux-native sound (pulseaudio/pipewire bypass of the browser)
- Multiple simultaneous audio tracks / mixing

---

## File structure

```
courant/
├── audio_downloader.py             # NEW : mirror of scene_downloader for audio files
├── data/
│   ├── scenes.json                 # existing
│   └── audio.json                  # NEW : audio track registry
├── paths.py                        # MODIFIED : audio_dir() helper
├── cli.py                          # MODIFIED : install/uninstall (systemd) + install-audio
├── web.py                          # MODIFIED : /audio/* mount + /api/audio endpoint
├── static/
│   ├── courant.css                 # MODIFIED : audio pill widget styling
│   └── audio-player.js             # NEW : HTMX-less mini player
├── templates/
│   └── base.html                   # MODIFIED : audio widget at bottom-right
.github/
└── workflows/
    └── publish.yml                 # NEW : on tag push, build wheel + upload to PyPI
docs/
└── INSTALL.md                      # NEW : per-distro install instructions
```

---

## Task 1 : systemd unit template + `courant install`

**Files:**
- Create: `courant/templates/systemd/courant.service.in` (template, not a Jinja template — just text with `@@VARS@@`)
- Modify: `courant/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1 : Create `courant/templates/systemd/courant.service.in`**

```ini
[Unit]
Description=Courant — a cozy reminder for developers
Documentation=https://github.com/BryanBradfo/courant
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=@@COURANT_BIN@@ start
Restart=on-failure
RestartSec=5s
Environment=COURANT_MANAGED_BY_SYSTEMD=1

[Install]
WantedBy=default.target
```

Make sure this file is included in the wheel (hatchling includes non-Python files in packages by default).

- [ ] **Step 2 : Write failing tests**

Append to `tests/test_cli.py` :

```python
def test_install_writes_systemd_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    # Mock systemctl to be present so the install path proceeds
    monkeypatch.setenv("PATH", "/usr/bin:" + os.environ.get("PATH", ""))

    # The install command should not actually enable / start the unit in tests —
    # we monkeypatch subprocess.run to capture invocations instead.
    calls: list[list[str]] = []
    import subprocess as sub_mod

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()

    monkeypatch.setattr(sub_mod, "run", fake_run)

    exit_code = main(["install"])
    assert exit_code == 0

    # Check the unit file was written
    unit_path = tmp_path / "config" / "systemd" / "user" / "courant.service"
    assert unit_path.exists()
    content = unit_path.read_text()
    assert "Courant" in content
    assert "ExecStart=" in content
    assert "@@COURANT_BIN@@" not in content  # substitution happened

    # Check systemctl was called
    systemctl_calls = [c for c in calls if c[0].endswith("systemctl")]
    assert any("daemon-reload" in " ".join(c) for c in systemctl_calls)
    assert any("enable" in " ".join(c) and "courant.service" in " ".join(c) for c in systemctl_calls)


def test_uninstall_removes_systemd_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PATH", "/usr/bin:" + os.environ.get("PATH", ""))

    # Pre-create a fake unit file
    unit_path = tmp_path / "config" / "systemd" / "user" / "courant.service"
    unit_path.parent.mkdir(parents=True)
    unit_path.write_text("fake unit")

    calls: list[list[str]] = []
    import subprocess as sub_mod

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()

    monkeypatch.setattr(sub_mod, "run", fake_run)

    exit_code = main(["uninstall"])
    assert exit_code == 0
    assert not unit_path.exists()
```

- [ ] **Step 3 : Implement `_run_install` and `_run_uninstall` in `cli.py`**

Add subcommands :

```python
    subparsers.add_parser("install", help="Create + enable the systemd user service")
    subparsers.add_parser("uninstall", help="Disable + remove the systemd user service")
```

Add dispatch in `main()` :

```python
    if args.command == "install":
        return _run_install()
    if args.command == "uninstall":
        return _run_uninstall()
```

Implement the functions :

```python
import shutil
import subprocess


_SYSTEMD_UNIT_PATH_RELATIVE = "systemd/user/courant.service"


def _systemd_unit_path() -> Path:
    return config_dir().parent / _SYSTEMD_UNIT_PATH_RELATIVE
    # Actually: XDG_CONFIG_HOME/systemd/user/courant.service
    # config_dir() returns XDG_CONFIG_HOME/courant, so .parent gives XDG_CONFIG_HOME


def _render_unit_template() -> str:
    """Read the bundled template and substitute @@COURANT_BIN@@."""
    from importlib import resources
    template = resources.files("courant.templates.systemd").joinpath("courant.service.in").read_text()
    courant_bin = shutil.which("courant") or "/usr/local/bin/courant"
    return template.replace("@@COURANT_BIN@@", courant_bin)


def _run_install() -> int:
    if shutil.which("systemctl") is None:
        print("systemctl not found. systemd integration is only available on systemd-managed Linux.")
        return 1

    # Compute path : XDG_CONFIG_HOME/systemd/user/courant.service
    config_root = config_dir().parent  # config_dir() is .../courant, parent is XDG_CONFIG_HOME
    unit_path = config_root / "systemd" / "user" / "courant.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(_render_unit_template())
    print(f"Wrote {unit_path}")

    # Reload systemd's user manager + enable + start
    for cmd in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "courant.service"],
        ["systemctl", "--user", "start", "courant.service"],
    ):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command failed : {' '.join(cmd)}")
            print(result.stderr)
            return 1
        print(f"✓ {' '.join(cmd)}")

    print("\nCourant is now running as a systemd user service.")
    print("Web UI : http://localhost:8765")
    print("Status : courant status   or   systemctl --user status courant.service")
    return 0


def _run_uninstall() -> int:
    config_root = config_dir().parent
    unit_path = config_root / "systemd" / "user" / "courant.service"
    if not unit_path.exists():
        print("Courant systemd service is not installed.")
        return 0

    if shutil.which("systemctl"):
        for cmd in (
            ["systemctl", "--user", "stop", "courant.service"],
            ["systemctl", "--user", "disable", "courant.service"],
            ["systemctl", "--user", "daemon-reload"],
        ):
            subprocess.run(cmd, capture_output=True, text=True)

    unit_path.unlink()
    print(f"Removed {unit_path}")
    print("Courant systemd service uninstalled. Your data (DB, videos) is unchanged.")
    return 0
```

Adjust the path computation if `config_dir()` doesn't have a `.parent` that gives XDG_CONFIG_HOME. Verify by inspecting `paths.py`. The cleanest path : import `_xdg("XDG_CONFIG_HOME", ".config")` directly, or add a `config_root()` helper in `paths.py`.

Actually : add this to `paths.py` :

```python
def systemd_user_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "systemd" / "user"
```

Then in `cli.py` :

```python
from courant.paths import systemd_user_dir

def _systemd_unit_path() -> Path:
    return systemd_user_dir() / "courant.service"
```

- [ ] **Step 4 : Make `courant/templates/systemd/` a package**

Create `courant/templates/systemd/__init__.py` (empty file). `courant/templates/__init__.py` may already exist — verify.

Actually, FastAPI's `Jinja2Templates(directory=...)` doesn't require `templates/` to be a Python package. But `importlib.resources.files("courant.templates.systemd")` does — it needs `__init__.py`.

Solution : keep `courant/templates/` as a non-package directory for Jinja, and put the systemd template under `courant/data/systemd/` instead (which IS a package since `courant.data` already has `__init__.py`). Adjust the import to :

```python
template = resources.files("courant.data").joinpath("systemd/courant.service.in").read_text()
```

Wait, that requires `systemd/` to be a subdirectory. `importlib.resources.files(pkg).joinpath("path/to/file")` works as long as the file is present in the package's installed files. With hatchling, this should be included automatically.

Simpler still : put the template directly under `courant/data/` :

```
courant/data/
├── __init__.py
├── default_reminders.json
├── scenes.json
└── courant.service.in
```

And import as `resources.files("courant.data").joinpath("courant.service.in")`.

Use this simpler structure. Move the template there.

- [ ] **Step 5 : Run tests, verify pass**

```bash
source .venv/bin/activate
pytest -v
```

Expect 91 passing (89 + 2 new).

- [ ] **Step 6 : Commit**

```bash
git add -A
git commit -m "feat(cli): install / uninstall commands for systemd user service"
```

---

## Task 2 : Audio file registry + download manager

**Files:**
- Create: `courant/data/audio.json`
- Create: `courant/audio_downloader.py`
- Modify: `courant/paths.py` (add `audio_dir()`)
- Modify: `courant/web.py` (mount `/audio` + `/api/audio`)
- Modify: `courant/cli.py` (install-audio command)
- Create: `tests/test_audio_downloader.py`

- [ ] **Step 1 : Create `courant/data/audio.json`**

```json
{
  "rain": {
    "name": "Rain",
    "url": "/audio/rain.mp3",
    "download_url": "https://github.com/BryanBradfo/courant/releases/download/audio-v1/rain.mp3",
    "author": "Pixabay contributor",
    "license": "Pixabay Content License",
    "source": "https://pixabay.com/sound-effects/search/rain/"
  },
  "ocean": {
    "name": "Ocean waves",
    "url": "/audio/ocean.mp3",
    "download_url": "https://github.com/BryanBradfo/courant/releases/download/audio-v1/ocean.mp3",
    "author": "Pixabay contributor",
    "license": "Pixabay Content License",
    "source": "https://pixabay.com/sound-effects/search/ocean/"
  },
  "cafe": {
    "name": "Café ambiance",
    "url": "/audio/cafe.mp3",
    "download_url": "https://github.com/BryanBradfo/courant/releases/download/audio-v1/cafe.mp3",
    "author": "Pixabay contributor",
    "license": "Pixabay Content License",
    "source": "https://pixabay.com/sound-effects/search/cafe/"
  },
  "fireplace": {
    "name": "Fireplace",
    "url": "/audio/fireplace.mp3",
    "download_url": "https://github.com/BryanBradfo/courant/releases/download/audio-v1/fireplace.mp3",
    "author": "Pixabay contributor",
    "license": "Pixabay Content License",
    "source": "https://pixabay.com/sound-effects/search/fireplace/"
  }
}
```

The user will curate the actual `.mp3` files (10-30s loops, ~500 KB each) and we'll upload them to a `audio-v1` GitHub release in Task 5.

- [ ] **Step 2 : Add `audio_dir()` to `paths.py`**

```python
def audio_dir() -> Path:
    return data_dir() / "audio"
```

Update `ensure_dirs()` to include it.

- [ ] **Step 3 : Create `courant/audio_downloader.py`**

Identical structure to `scene_downloader.py` but pointing to `audio.json` and `audio_dir()`. Specifically :

```python
"""Download manager for ambient audio tracks. Mirror of scene_downloader."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from courant.paths import audio_dir

logger = logging.getLogger(__name__)


@dataclass
class AudioStatus:
    slug: str
    name: str
    local_path: Path
    download_url: str
    is_installed: bool
    size_bytes: int | None


def _load_registry() -> dict[str, dict[str, str]]:
    from typing import cast
    with resources.files("courant.data").joinpath("audio.json").open("r") as f:
        return cast(dict[str, dict[str, str]], json.load(f))


def list_tracks() -> list[AudioStatus]:
    registry = _load_registry()
    adir = audio_dir()
    result = []
    for slug, meta in registry.items():
        path = adir / f"{slug}.mp3"
        installed = path.exists() and path.stat().st_size > 0
        size = path.stat().st_size if installed else None
        result.append(AudioStatus(
            slug=slug,
            name=meta["name"],
            local_path=path,
            download_url=meta.get("download_url", ""),
            is_installed=installed,
            size_bytes=size,
        ))
    return result


def missing_tracks() -> list[AudioStatus]:
    return [t for t in list_tracks() if not t.is_installed]


def download_track(track: AudioStatus, progress_callback: Callable[[int, int], None] | None = None) -> bool:
    if not track.download_url:
        return False
    track.local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = track.local_path.with_suffix(".mp3.part")
    try:
        with urllib.request.urlopen(track.download_url) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            written = 0
            with tmp.open("wb") as out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    written += len(chunk)
                    if progress_callback and total:
                        progress_callback(written, total)
        tmp.rename(track.local_path)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        logger.error("Failed to download %s : %s", track.download_url, e)
        tmp.unlink(missing_ok=True)
        return False


def install_all(only_missing: bool = True) -> tuple[int, int]:
    tracks = missing_tracks() if only_missing else list_tracks()
    if not tracks:
        return 0, 0
    succeeded = 0
    for i, t in enumerate(tracks, 1):
        print(f"[{i}/{len(tracks)}] {t.name} ({t.slug})")
        print(f"  Downloading from {t.download_url}")
        def on_progress(done: int, total: int) -> None:
            pct = done / total * 100
            print(f"\r  {done/1024:.0f} / {total/1024:.0f} KB ({pct:.0f}%)", end="", flush=True)
        ok = download_track(t, progress_callback=on_progress)
        print()
        if ok:
            print(f"  ✓ Installed at {t.local_path}")
            succeeded += 1
        else:
            print(f"  ✗ Failed (see log)")
    return succeeded, len(tracks)
```

- [ ] **Step 4 : Mount `/audio` in `web.py`**

After the `/videos` mount, add :

```python
from courant.paths import audio_dir

audio_path = audio_dir()
audio_path.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_path)), name="audio")

@app.get("/api/audio")
async def api_audio() -> dict[str, dict[str, str]]:
    return _AUDIO_REGISTRY
```

Load the registry at startup :

```python
def _load_audio_registry() -> dict[str, dict[str, str]]:
    from typing import cast
    with resources.files("courant.data").joinpath("audio.json").open("r") as f:
        return cast(dict[str, dict[str, str]], json.load(f))

_AUDIO_REGISTRY = _load_audio_registry()
```

- [ ] **Step 5 : Add `install-audio` subcommand to `cli.py`**

```python
    subparsers.add_parser("install-audio", help="Download ambient audio tracks")
```

```python
    if args.command == "install-audio":
        return _run_install_audio()


def _run_install_audio() -> int:
    from courant.audio_downloader import install_all, missing_tracks
    missing = missing_tracks()
    if not missing:
        print("All audio tracks already installed.")
        return 0
    print(f"Installing {len(missing)} missing audio tracks")
    succeeded, total = install_all(only_missing=True)
    return 0 if succeeded == total else 1
```

- [ ] **Step 6 : Write tests in `tests/test_audio_downloader.py`**

Same structure as `tests/test_scene_downloader.py` but for audio.

- [ ] **Step 7 : Run tests, lint, type-check, commit**

```bash
pytest -v && ruff check courant tests && mypy courant
git add -A
git commit -m "feat(audio): registry + download manager + install-audio CLI command"
```

---

## Task 3 : Audio player UI

**Files:**
- Modify: `courant/templates/base.html` (add player widget)
- Modify: `courant/static/courant.css` (style player)
- Create: `courant/static/audio-player.js` (play/pause logic)
- Modify: `courant/web.py` (settings handler exposes audio_tracks)

- [ ] **Step 1 : Player widget HTML**

In `base.html`, add right after the `<canvas>` / `<video>` element :

```html
<div id="audio-player" class="audio-player">
  <audio id="audio-element" loop preload="none"></audio>
  <button id="audio-toggle" class="audio-toggle" aria-label="Play/pause ambient audio">
    ♪
  </button>
  <span id="audio-track-name" class="audio-track-name">—</span>
  <select id="audio-select" class="cozy-select audio-select" aria-label="Select audio track">
    <option value="">Silence</option>
    <!-- options populated by JS from /api/audio -->
  </select>
  <input id="audio-volume" type="range" min="0" max="100" value="50"
         class="audio-volume" aria-label="Volume">
</div>
```

- [ ] **Step 2 : CSS for `.audio-player` (append to `courant.css`)**

```css
.audio-player {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--text-primary);
  font-family: var(--font-ui);
  font-size: 0.875rem;
}
.audio-toggle {
  background: none; border: none; color: var(--text-primary);
  font-size: 1.25rem; cursor: pointer; padding: 0;
}
.audio-track-name { min-width: 4rem; }
.audio-select { padding: 0.25rem 0.5rem; font-size: 0.8rem; }
.audio-volume { width: 80px; accent-color: var(--accent-blue); }
```

- [ ] **Step 3 : `courant/static/audio-player.js`**

```javascript
// audio-player.js — manages the ambient audio mini-player.

const player = document.getElementById('audio-player');
const audio = document.getElementById('audio-element');
const toggle = document.getElementById('audio-toggle');
const trackName = document.getElementById('audio-track-name');
const select = document.getElementById('audio-select');
const volume = document.getElementById('audio-volume');

let tracks = {};

async function loadTrackList() {
  try {
    const resp = await fetch('/api/audio');
    tracks = await resp.json();
    // Populate select
    for (const [slug, meta] of Object.entries(tracks)) {
      const opt = document.createElement('option');
      opt.value = slug;
      opt.textContent = meta.name;
      select.appendChild(opt);
    }
  } catch (e) {
    console.warn('Failed to load audio registry', e);
  }
}

function setTrack(slug) {
  if (!slug) {
    audio.pause();
    audio.removeAttribute('src');
    trackName.textContent = '—';
    toggle.textContent = '♪';
    return;
  }
  const meta = tracks[slug];
  if (!meta) return;
  audio.src = meta.url;
  trackName.textContent = meta.name;
  audio.play().then(() => {
    toggle.textContent = '⏸';
    localStorage.setItem('courant_audio_slug', slug);
  }).catch((err) => {
    console.warn('Audio play failed (file missing?)', err);
    toggle.textContent = '♪';
  });
}

toggle.addEventListener('click', () => {
  if (!audio.src) return;
  if (audio.paused) {
    audio.play();
    toggle.textContent = '⏸';
  } else {
    audio.pause();
    toggle.textContent = '♪';
  }
});

select.addEventListener('change', (e) => {
  setTrack(e.target.value);
});

volume.addEventListener('input', (e) => {
  audio.volume = e.target.value / 100;
  localStorage.setItem('courant_audio_volume', e.target.value);
});

// Restore last state
(async () => {
  await loadTrackList();
  const savedVolume = localStorage.getItem('courant_audio_volume');
  if (savedVolume) {
    volume.value = savedVolume;
    audio.volume = savedVolume / 100;
  }
  const savedSlug = localStorage.getItem('courant_audio_slug');
  if (savedSlug && tracks[savedSlug]) {
    select.value = savedSlug;
    // Don't autoplay — browsers block autoplay with sound. User must click ▶.
    audio.src = tracks[savedSlug].url;
    trackName.textContent = tracks[savedSlug].name;
  }
})();
```

Load the script in `base.html` after the scene-loader :

```html
<script src="/static/audio-player.js"></script>
```

- [ ] **Step 4 : Run tests + commit**

```bash
pytest -v && ruff check courant tests && mypy courant
git add -A
git commit -m "feat(audio): floating player widget with track selector and volume"
```

---

## Task 4 : PyPI publishing prep + GitHub Actions

**Files:**
- Modify: `pyproject.toml` (metadata polish, classifiers)
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1 : Polish `pyproject.toml` metadata**

Add (after the existing `[project]` keys) :

```toml
keywords = ["reminder", "linux", "desktop", "notifications", "wellness", "lofi", "cozy"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Environment :: Web Environment",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Office/Business :: Scheduling",
]

[project.urls]
Homepage      = "https://github.com/BryanBradfo/courant"
Issues        = "https://github.com/BryanBradfo/courant/issues"
Documentation = "https://github.com/BryanBradfo/courant#readme"
Source        = "https://github.com/BryanBradfo/courant"
Changelog     = "https://github.com/BryanBradfo/courant/releases"
```

- [ ] **Step 2 : Create `.github/workflows/publish.yml`**

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*.*.*"

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install build tools
        run: pip install build twine
      - name: Build distribution
        run: python -m build
      - name: Check distribution
        run: twine check dist/*
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write   # for OIDC trusted publishing
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

This uses PyPI **Trusted Publishing** (no API token needed). Setup steps (manual, in PyPI dashboard) :

1. Reserve the project name `courant` on PyPI by uploading a 0.0.0 stub OR have the maintainer configure trusted publishing FIRST then push a tag.
2. On https://pypi.org/manage/account/publishing/ , add a Pending Publisher : repo `BryanBradfo/courant`, workflow `publish.yml`, environment `pypi`.

These steps are documented in `docs/INSTALL.md` (Task 5).

- [ ] **Step 3 : Test local build**

```bash
source .venv/bin/activate
pip install build twine
python -m build
twine check dist/*
ls dist/
```

Should produce `dist/courant-0.1.0-py3-none-any.whl` and `dist/courant-0.1.0.tar.gz`, both check-clean.

If twine reports issues (missing fields, broken README markup), fix them.

- [ ] **Step 4 : Commit**

```bash
git add -A
git commit -m "build(pypi): metadata polish + publish workflow via OIDC trusted publishing"
```

---

## Task 5 : INSTALL.md + final README polish

**Files:**
- Create: `docs/INSTALL.md`
- Modify: `README.md`

- [ ] **Step 1 : Create `docs/INSTALL.md`**

```markdown
# Installing Courant

## End users

The easiest path — `pipx` installs Courant in an isolated venv :

```
pipx install courant
courant install-scenes        # ~10 MB of ambient videos
courant install-audio         # ~2 MB of ambient sounds (optional)
courant install               # creates a systemd user service (auto-starts at login)
```

That's it. The web UI is at <http://localhost:8765>.

## Development install

```
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
```

- [ ] **Step 2 : Update README.md Status**

```markdown
## Status

- ✅ Phase 1 — Core CLI + desktop notifications
- ✅ Phase 2 — Functional web UI (FastAPI + HTMX)
- ✅ Phase 3 — Cozy aesthetic with ambient video scenes
- ✅ Phase 4 — systemd integration + PyPI publish + ambient audio
```

Add to install snippet :

```markdown
## Quick start

```
pipx install courant
courant install-scenes
courant install-audio    # optional
courant install          # systemd user service
```

## Manual / dev install

(... existing dev install instructions ...)
```

- [ ] **Step 3 : Commit, tag, push**

```bash
git add -A
git commit -m "docs: INSTALL.md + Phase 4 status in README"
git tag -a phase-4-complete -m "Phase 4 : systemd + PyPI + audio"
```

(Tag will be pushed in Task 7.)

---

## Task 6 : Audio files curation by user

This is a **user task**, not a subagent task. After the rest of the code lands :

- [ ] User curates 4 ambient sounds from Pixabay sound effects :
  - rain (~30s loop, ~500 KB MP3)
  - ocean waves
  - café ambiance
  - fireplace

- [ ] User re-encodes them with the same approach as videos but for audio :

```bash
ffmpeg -i source.mp3 -t 30 -b:a 96k output.mp3
```

(96 kbps mono is fine for ambient loops, smaller files.)

- [ ] User puts them in `~/.local/share/courant/audio/` with the correct slugs : `rain.mp3`, `ocean.mp3`, `cafe.mp3`, `fireplace.mp3`.

- [ ] User uploads to a new GitHub release `audio-v1` :

```bash
gh release create audio-v1 --title "Ambient audio — v1 (4 lofi loops)" \
  ~/.local/share/courant/audio/rain.mp3 \
  ~/.local/share/courant/audio/ocean.mp3 \
  ~/.local/share/courant/audio/cafe.mp3 \
  ~/.local/share/courant/audio/fireplace.mp3
```

---

## Task 7 : Final lint/type/test + push + release

- [ ] **Step 1 : Final pipeline**

```bash
source .venv/bin/activate
ruff check courant tests
mypy courant
pytest -v
```

All green expected.

- [ ] **Step 2 : Push branch + open PR**

```bash
git push -u origin phase-4-polish
gh pr create --base main --head phase-4-polish \
  --title "Phase 4 : systemd + PyPI + audio player" \
  --body "Adds systemd user service integration, PyPI publish workflow (OIDC trusted publishing), and a floating audio player widget with 4 lo-fi ambient tracks. Closes the v1 roadmap."
```

- [ ] **Step 3 : Wait for CI, merge, push tag**

```bash
gh pr checks $(gh pr view --json number --jq .number)
# Wait until all green, then :
gh pr merge --merge
git checkout main && git pull
git push origin phase-4-complete

# Create GitHub release for Phase 4
gh release create phase-4-complete \
  --title "Phase 4 — Polish & Distribution" \
  --notes "v1 roadmap complete. Courant is now installable with \`pipx install courant\`, auto-starts at login via systemd user service, and ships with a floating audio player for lo-fi ambient sounds."
```

- [ ] **Step 4 : (Optional) Tag for PyPI**

```bash
# After PyPI Trusted Publishing is configured by the maintainer :
git tag v0.1.0
git push origin v0.1.0
# Workflow runs automatically and publishes courant 0.1.0 to PyPI.
```

---

## Phase 4 Done ✓

At this point :

- `pipx install courant` works (assuming PyPI publish succeeded)
- `courant install` sets up a systemd user service that auto-starts at login
- The web UI has a working audio player widget with 4 ambient tracks
- ~95 tests passing
- Public OSS project complete in its v1 form

**What's next** : community, feedback, real users. Phase 5 (i18n, mobile responsive, webhooks) only if there's demand.
