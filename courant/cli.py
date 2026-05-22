"""Command-line entry point for Courant.

`main(argv=None)` is the testable function. The console_script `courant`
calls main() with sys.argv[1:].
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]

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
    except Exception as exc:
        logger.warning("Falling back to FakeNotifier (no notifications): %s", exc)
        return FakeNotifier()


def _run_daemon() -> int:
    _setup_logging()
    backup_if_stale(db_path())
    conn = connect(str(db_path()))
    migrate(conn)

    from courant.scene_downloader import missing_scenes
    missing = missing_scenes()
    if missing:
        names = ", ".join(m.slug for m in missing)
        logger.info(
            "%d scene videos missing (%s). Run `courant install-scenes` to fetch them (~10 MB).",
            len(missing), names,
        )

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

    try:
        # uvicorn handles SIGTERM/SIGINT internally and returns cleanly
        from courant.web_runner import run_server
        run_server(service)
    finally:
        rs.shutdown()
        conn.close()
    return 0


def _run_install_scenes() -> int:
    from courant.scene_downloader import install_all, missing_scenes
    missing = missing_scenes()
    if not missing:
        print("All scenes already installed.")
        return 0
    print(f"Installing {len(missing)} missing scenes to {missing[0].local_path.parent}")
    print()
    succeeded, total = install_all(only_missing=True)
    print()
    if succeeded == total:
        print(f"✓ Installed {succeeded} scenes successfully.")
        return 0
    else:
        print(f"⚠ {succeeded}/{total} scenes installed (some failed — check logs).")
        return 1


def _run_status() -> int:
    db = db_path()
    if not db.exists():
        print("Courant not initialized (no database found).")
        print(f"Expected at: {db}")
        return 0

    conn = connect(str(db))
    try:
        migrate(conn)  # ensure schema if file exists but is empty
        service = ReminderService(conn)
        reminders = service.list_reminders()
    finally:
        conn.close()

    print(f"Courant — database at {db}")
    print(f"Reminders configured: {len(reminders)}")
    for r in reminders:
        status = "enabled" if r.enabled else "disabled"
        print(f"  [{r.id:>2}] {r.name} ({status})")
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
    subparsers.add_parser(
        "install-scenes",
        help="Download the 6 default ambient scene videos (~10 MB total)",
    )

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

    if args.command == "install-scenes":
        return _run_install_scenes()

    print(f"command '{args.command}' not yet implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
