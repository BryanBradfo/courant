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
    then verify the DB was created and migrated."""
    # The default_reminders seed lands in Task 20. For now, just verify the DB
    # is created and migrated.
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
    conn.close()
    assert {"reminders", "events", "settings"}.issubset(tables)
