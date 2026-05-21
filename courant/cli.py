"""Command-line entry point for Courant.

`main(argv=None)` is the testable function. The console_script `courant`
calls main() with sys.argv[1:].
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import signal
import subprocess
import sys
import time as time_module

from apscheduler.schedulers.background import BackgroundScheduler

from courant import __version__
from courant.notifier import DesktopNotifier, FakeNotifier, Notifier
from courant.paths import db_path, ensure_dirs, log_path
from courant.repository import backup_if_stale, connect, migrate
from courant.scheduler import ReminderScheduler
from courant.service import ReminderService

logger = logging.getLogger("courant")


def _setup_logging() -> None:
    ensure_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path()),
        ],
    )


def _build_notifier() -> Notifier:
    """Try DesktopNotifier; fall back to FakeNotifier on failure (logged)."""
    try:
        return DesktopNotifier(app_name="Courant")
    except Exception as exc:  # noqa: BLE001 — fallback is intentional
        logger.warning("Falling back to FakeNotifier (no notifications): %s", exc)
        return FakeNotifier()


def _run_daemon() -> int:
    _setup_logging()
    ensure_dirs()
    backup_if_stale(db_path())
    conn = connect(str(db_path()))
    migrate(conn)

    service = ReminderService(conn)
    seeded = service.seed_defaults_if_empty()
    if seeded > 0:
        logger.info("Seeded %d default reminders on first launch", seeded)
    notifier = _build_notifier()
    apsched = BackgroundScheduler()
    rs = ReminderScheduler(scheduler=apsched, service=service, notifier=notifier)
    rs.sync_jobs()
    rs.start()

    logger.info("Courant daemon started (PID %d)", os.getpid())

    stop_requested = False

    def _on_signal(signum, _frame):
        nonlocal stop_requested
        logger.info("Received signal %d, shutting down", signum)
        stop_requested = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    try:
        while not stop_requested:
            time_module.sleep(0.5)
    finally:
        rs.shutdown()
        conn.close()
    return 0


def _run_status() -> int:
    db = db_path()
    if not db.exists():
        print("Courant not initialized (no database found).")
        print(f"Expected at: {db}")
        return 0
    conn = connect(str(db))
    rows = conn.execute(
        "SELECT id, name, enabled FROM reminders ORDER BY id"
    ).fetchall()
    conn.close()
    if not rows:
        print("No reminders configured.")
    else:
        for row_id, name, enabled in rows:
            state = "enabled" if enabled else "disabled"
            print(f"  [{row_id:>2}] {name} ({state})")
    return 0


def _run_stop() -> int:
    if shutil.which("systemctl") is None:
        print(
            "systemctl not found. "
            "If you ran `courant start` in foreground, stop it with Ctrl+C."
        )
        return 0
    result = subprocess.run(
        ["systemctl", "--user", "stop", "courant.service"],
        check=False,
    )
    if result.returncode == 0:
        print("Courant service stopped.")
    else:
        print("No running Courant service found (or stop failed).")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="courant",
        description="Un rappel cozy pour les devs : eau, yeux, étirements.",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    subparsers.add_parser("version", help="Print version and exit")
    subparsers.add_parser("start", help="Start the daemon (foreground)")
    subparsers.add_parser("stop", help="Stop the systemd-managed daemon")
    subparsers.add_parser("status", help="Show daemon status and URL")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 2

    if args.command == "version":
        print(f"courant {__version__}")
        return 0

    if args.command == "start":
        return _run_daemon()

    if args.command == "status":
        return _run_status()

    if args.command == "stop":
        return _run_stop()

    print(f"command '{args.command}' not yet implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
