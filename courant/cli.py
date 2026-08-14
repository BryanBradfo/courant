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
from courant.events_bus import EventBus
from courant.notifier import DesktopNotifier, FakeNotifier, Notifier
from courant.paths import db_path, ensure_dirs, log_path, systemd_user_dir
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
    bus = EventBus()
    apsched = BackgroundScheduler()
    rs = ReminderScheduler(scheduler=apsched, service=service, notifier=notifier, bus=bus)
    rs.sync_jobs()
    rs.start()

    logger.info("Courant daemon started (PID %d)", os.getpid())

    try:
        # uvicorn handles SIGTERM/SIGINT internally and returns cleanly
        from courant.web_runner import run_server
        run_server(service, bus=bus)
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


def _render_unit_template() -> str:
    """Read the bundled template and substitute @@COURANT_BIN@@."""
    from importlib import resources
    template = resources.files("courant.data").joinpath("courant.service.in").read_text()
    courant_bin = shutil.which("courant") or "/usr/local/bin/courant"
    return template.replace("@@COURANT_BIN@@", courant_bin)


def _run_install() -> int:
    if shutil.which("systemctl") is None:
        print(
            "systemctl not found. systemd integration is only available on systemd-managed Linux."
        )
        return 1

    unit_path = systemd_user_dir() / "courant.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    unit_path.write_text(_render_unit_template())
    print(f"Wrote {unit_path}")

    for cmd in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "courant.service"],
        ["systemctl", "--user", "start", "courant.service"],
    ):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command failed : {' '.join(cmd)}")
            print(result.stderr)
            return 1
        print(f"✓ {' '.join(cmd)}")

    print("\nCourant is now running as a systemd user service.")
    print("Web UI : http://localhost:8765")
    print("Status : courant status   or   systemctl --user status courant.service")
    return 0


def _run_uninstall() -> int:
    unit_path = systemd_user_dir() / "courant.service"
    if not unit_path.exists():
        print("Courant systemd service is not installed.")
        return 0

    if shutil.which("systemctl"):
        for cmd in (
            ["systemctl", "--user", "stop", "courant.service"],
            ["systemctl", "--user", "disable", "courant.service"],
            ["systemctl", "--user", "daemon-reload"],
        ):
            subprocess.run(cmd, capture_output=True, text=True)

    unit_path.unlink()
    print(f"Removed {unit_path}")
    print("Courant systemd service uninstalled. Your data (DB, videos) is unchanged.")
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


def _run_install_audio() -> int:
    from courant.audio_downloader import install_all, missing_tracks
    missing = missing_tracks()
    if not missing:
        print("All audio tracks already installed.")
        return 0
    print(f"Installing {len(missing)} missing audio tracks")
    succeeded, total = install_all(only_missing=True)
    print()
    if succeeded == total:
        print(f"✓ Installed {succeeded} audio tracks successfully.")
        return 0
    else:
        print(f"⚠ {succeeded}/{total} audio tracks installed (some failed — check logs).")
        return 1


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
    subparsers.add_parser("install", help="Create + enable the systemd user service")
    subparsers.add_parser("uninstall", help="Disable + remove the systemd user service")
    subparsers.add_parser("install-audio", help="Download ambient audio tracks")

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

    if args.command == "install":
        return _run_install()

    if args.command == "uninstall":
        return _run_uninstall()

    if args.command == "install-audio":
        return _run_install_audio()

    print(f"command '{args.command}' not yet implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
