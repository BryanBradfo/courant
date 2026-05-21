"""Command-line entry point for Courant.

`main(argv=None)` is the testable function. The console_script `courant`
calls main() with sys.argv[1:].
"""
from __future__ import annotations

import argparse
import sys

from courant import __version__


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

    # start/stop/status implemented in subsequent tasks
    print(f"command '{args.command}' not yet implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
