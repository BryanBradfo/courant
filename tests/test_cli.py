"""Tests for the courant CLI."""
from __future__ import annotations

import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from courant.cli import main


def test_version_command(capsys: pytest.CaptureFixture[str]):
    exit_code = main(["version"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "courant" in out.lower()
    # Expect a SemVer-ish string
    assert any(ch.isdigit() for ch in out)


def test_no_args_prints_help_and_exits_nonzero(capsys: pytest.CaptureFixture[str]):
    exit_code = main([])
    assert exit_code != 0
    err_or_out = capsys.readouterr()
    combined = err_or_out.out + err_or_out.err
    assert "usage" in combined.lower()


def test_unknown_command_errors(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit) as excinfo:
        main(["does-not-exist"])
    assert excinfo.value.code != 0


def test_start_creates_db_and_seeds_default_reminders(
    tmp_path: Path,
):
    """Spawn `python -m courant.cli start` in a subprocess, give it 2s, kill it,
    then verify the DB was created, migrated, and seeded with default reminders."""
    env = {
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "PATH": __import__("os").environ.get("PATH", ""),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "courant.cli", "start"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(2)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=5)

    db = tmp_path / "data" / "courant" / "courant.db"
    assert db.exists()
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"reminders", "events", "settings"}.issubset(tables)
    rows = conn.execute("SELECT id FROM reminders").fetchall()
    conn.close()
    assert len(rows) == 3, f"Expected 3 seeded reminders, got {len(rows)}"


def test_status_when_no_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """status exits 0 and explains no database when DB doesn't exist."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    exit_code = main(["status"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "not initialized" in out.lower() or "no database" in out.lower()


def test_status_with_db_shows_reminder_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """status shows reminder rows when DB exists."""
    from courant.repository import connect, migrate

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    # Create the DB directory and a DB with one reminder
    db_dir = tmp_path / "data" / "courant"
    db_dir.mkdir(parents=True)
    db_file = db_dir / "courant.db"
    conn = connect(str(db_file))
    migrate(conn)
    conn.execute(
        "INSERT INTO reminders"
        " (name, message, interval_minutes, created_at, enabled)"
        " VALUES (?, ?, ?, ?, ?)",
        ("Eau", "Bois de l'eau !", 60, "2026-01-01T00:00:00", 1),
    )
    conn.commit()
    conn.close()

    exit_code = main(["status"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "1" in out
    assert "eau" in out.lower() or "reminder" in out.lower()


def test_stop_when_no_systemd_prints_instructions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """stop exits 0 and gives Ctrl+C instructions when systemctl is absent."""
    # Create an empty dir so PATH lookup finds nothing
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()
    monkeypatch.setenv("PATH", str(empty_bin))

    exit_code = main(["stop"])
    assert exit_code == 0
    out = capsys.readouterr().out
    combined = out.lower()
    assert "systemd" in combined or "ctrl" in combined
