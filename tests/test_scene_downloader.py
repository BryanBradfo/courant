"""Tests for the scene download manager."""
from __future__ import annotations

from pathlib import Path

import pytest

from courant.scene_downloader import list_scenes, missing_scenes


def test_list_scenes_reports_install_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    scenes = list_scenes()
    # We have 6 scenes in scenes.json
    assert len(scenes) == 6
    # None should be installed in a fresh tmp dir
    assert all(not s.is_installed for s in scenes)


def test_list_scenes_detects_installed_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    videos_dir = tmp_path / "courant" / "videos"
    videos_dir.mkdir(parents=True)
    (videos_dir / "cozy-cabin.mp4").write_bytes(b"fake video data")

    scenes = list_scenes()
    cozy = next(s for s in scenes if s.slug == "cozy-cabin")
    assert cozy.is_installed
    assert cozy.size_bytes == len(b"fake video data")
    # Others still uninstalled
    others = [s for s in scenes if s.slug != "cozy-cabin"]
    assert all(not s.is_installed for s in others)


def test_missing_scenes_filters_correctly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    videos_dir = tmp_path / "courant" / "videos"
    videos_dir.mkdir(parents=True)
    (videos_dir / "cozy-cabin.mp4").write_bytes(b"data")

    missing = missing_scenes()
    slugs = {s.slug for s in missing}
    assert "cozy-cabin" not in slugs
    assert len(missing) == 5  # 6 - 1 installed
