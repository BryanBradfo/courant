"""XDG Base Directory paths for Courant runtime data."""
from __future__ import annotations

import os
from pathlib import Path


def _xdg(env_var: str, default_subpath: str) -> Path:
    base = os.environ.get(env_var)
    if base:
        return Path(base)
    return Path.home() / default_subpath


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "courant"


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "courant"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "courant"


def db_path() -> Path:
    return data_dir() / "courant.db"


def log_path() -> Path:
    return cache_dir() / "logs" / "courant.log"


def ensure_dirs() -> None:
    for d in (config_dir(), data_dir(), cache_dir(), cache_dir() / "logs"):
        d.mkdir(parents=True, exist_ok=True)
