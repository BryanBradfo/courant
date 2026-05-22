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
    size_bytes: int | None  # None if not installed


def _load_registry() -> dict[str, dict[str, str]]:
    from typing import cast
    with resources.files("courant.data").joinpath("audio.json").open("r") as f:
        return cast(dict[str, dict[str, str]], json.load(f))


def list_tracks() -> list[AudioStatus]:
    """Inspect all audio tracks, return their install status."""
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
    """Audio tracks whose file is not installed locally."""
    return [t for t in list_tracks() if not t.is_installed]


def download_track(
    track: AudioStatus,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bool:
    """Download a single audio track. Returns True on success.

    progress_callback : optional callable(bytes_so_far, total_bytes).
    """
    if not track.download_url:
        logger.warning("No download_url for track %s", track.slug)
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
    except urllib.error.HTTPError as e:
        logger.error("HTTP %d downloading %s", e.code, track.download_url)
        tmp.unlink(missing_ok=True)
        return False
    except urllib.error.URLError as e:
        logger.error("Network error downloading %s : %s", track.download_url, e)
        tmp.unlink(missing_ok=True)
        return False


def install_all(only_missing: bool = True) -> tuple[int, int]:
    """Download all audio tracks (or only missing ones if only_missing=True).

    Returns (succeeded_count, total_attempted).
    """
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
        print()  # newline after progress
        if ok:
            print(f"  ✓ Installed at {t.local_path}")
            succeeded += 1
        else:
            print("  ✗ Failed (see log)")
    return succeeded, len(tracks)
