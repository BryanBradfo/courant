"""Download manager for ambient scene videos.

Videos are hosted as GitHub release assets. This module downloads them
to ~/.local/share/courant/videos/ on demand.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from courant.paths import videos_dir

logger = logging.getLogger(__name__)


@dataclass
class SceneStatus:
    slug: str
    name: str
    local_path: Path
    download_url: str
    is_installed: bool
    size_bytes: int | None  # None if not installed


def _load_registry() -> dict[str, dict[str, str]]:
    with resources.files("courant.data").joinpath("scenes.json").open("r") as f:
        data: dict[str, dict[str, str]] = json.load(f)
        return data


def list_scenes() -> list[SceneStatus]:
    """Inspect all scenes, return their install status."""
    registry = _load_registry()
    vdir = videos_dir()
    result = []
    for slug, meta in registry.items():
        path = vdir / f"{slug}.mp4"
        installed = path.exists() and path.stat().st_size > 0
        size = path.stat().st_size if installed else None
        result.append(SceneStatus(
            slug=slug,
            name=meta["name"],
            local_path=path,
            download_url=meta.get("download_url", ""),
            is_installed=installed,
            size_bytes=size,
        ))
    return result


def missing_scenes() -> list[SceneStatus]:
    """Scenes whose video file is not installed locally."""
    return [s for s in list_scenes() if not s.is_installed]


def download_scene(
    scene: SceneStatus,
    progress_callback: Callable[[int, int], None] | None = None,
) -> bool:
    """Download a single scene's video. Returns True on success.

    progress_callback : optional callable(bytes_so_far, total_bytes).
    """
    if not scene.download_url:
        logger.warning("No download_url for scene %s", scene.slug)
        return False

    scene.local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = scene.local_path.with_suffix(".mp4.part")

    try:
        with urllib.request.urlopen(scene.download_url) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            chunk = 64 * 1024
            written = 0
            with tmp_path.open("wb") as out:
                while True:
                    data = resp.read(chunk)
                    if not data:
                        break
                    out.write(data)
                    written += len(data)
                    if progress_callback and total:
                        progress_callback(written, total)
        tmp_path.rename(scene.local_path)
        return True
    except urllib.error.HTTPError as e:
        logger.error("HTTP %d downloading %s", e.code, scene.download_url)
        tmp_path.unlink(missing_ok=True)
        return False
    except urllib.error.URLError as e:
        logger.error("Network error downloading %s : %s", scene.download_url, e)
        tmp_path.unlink(missing_ok=True)
        return False


def install_all(only_missing: bool = True) -> tuple[int, int]:
    """Download all scenes (or only missing ones if only_missing=True).

    Returns (succeeded_count, total_attempted).
    """
    scenes = missing_scenes() if only_missing else list_scenes()
    if not scenes:
        return 0, 0

    succeeded = 0
    for i, scene in enumerate(scenes, 1):
        print(f"[{i}/{len(scenes)}] {scene.name} ({scene.slug})")
        print(f"  Downloading from {scene.download_url}")

        def on_progress(done: int, total: int) -> None:
            pct = done / total * 100
            mb = done / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            print(f"\r  {mb:.1f} / {total_mb:.1f} MB ({pct:.0f}%)", end="", flush=True)

        ok = download_scene(scene, progress_callback=on_progress)
        print()  # newline after progress
        if ok:
            print(f"  ✓ Installed at {scene.local_path}")
            succeeded += 1
        else:
            print("  ✗ Failed (see log)")
    return succeeded, len(scenes)
