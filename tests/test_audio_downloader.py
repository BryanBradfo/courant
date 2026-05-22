"""Tests for the audio download manager."""
from __future__ import annotations

from pathlib import Path

import pytest

from courant.audio_downloader import list_tracks, missing_tracks


def test_list_tracks_reports_install_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    tracks = list_tracks()
    # We have 6 tracks in audio.json
    assert len(tracks) == 6
    # None should be installed in a fresh tmp dir
    assert all(not t.is_installed for t in tracks)


def test_list_tracks_detects_installed_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    audio_dir = tmp_path / "courant" / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "cozy-night.mp3").write_bytes(b"fake audio data")

    tracks = list_tracks()
    cozy = next(t for t in tracks if t.slug == "cozy-night")
    assert cozy.is_installed
    assert cozy.size_bytes == len(b"fake audio data")
    # Others still uninstalled
    others = [t for t in tracks if t.slug != "cozy-night"]
    assert all(not t.is_installed for t in others)


def test_missing_tracks_filters_correctly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    audio_dir = tmp_path / "courant" / "audio"
    audio_dir.mkdir(parents=True)
    (audio_dir / "cozy-night.mp3").write_bytes(b"data")

    missing = missing_tracks()
    slugs = {t.slug for t in missing}
    assert "cozy-night" not in slugs
    assert len(missing) == 5  # 6 - 1 installed
