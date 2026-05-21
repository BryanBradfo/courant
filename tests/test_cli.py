"""Tests for the courant CLI."""
from __future__ import annotations

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
