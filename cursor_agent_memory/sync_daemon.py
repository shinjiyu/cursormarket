"""Periodic export of local Cursor sessions to a fixed directory (for MCP / cross-workspace use)."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .exporter import CursorMemoryExporter
from .paths import get_export_root


def run_once(
    *,
    include_raw: bool,
    limit: int | None,
    cursor_user_root: Path | None,
    projects_root: Path | None,
    compact: bool,
) -> dict:
    root = get_export_root()
    exporter = CursorMemoryExporter(
        output_dir=root,
        cursor_user_root=cursor_user_root,
        projects_root=projects_root,
        limit=limit,
        include_raw=include_raw,
        pretty=not compact,
    )
    return exporter.export()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cursor-agent-memory-sync",
        description="Periodically export Cursor local sessions to CURSOR_AGENT_MEMORY_EXPORT_DIR.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single export and exit (for Task Scheduler / cron).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("CURSOR_AGENT_MEMORY_SYNC_INTERVAL_SECONDS", "3600")),
        help="Seconds between exports when not using --once. Default from env or 3600.",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Also export raw composer payloads and transcript copies.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only export the N most recently updated sessions.",
    )
    parser.add_argument("--cursor-user-root", type=Path, default=None)
    parser.add_argument("--projects-root", type=Path, default=None)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    include_raw = args.include_raw or os.environ.get("CURSOR_AGENT_MEMORY_INCLUDE_RAW", "").lower() in (
        "1",
        "true",
        "yes",
    )

    if args.once:
        summary = run_once(
            include_raw=include_raw,
            limit=args.limit,
            cursor_user_root=args.cursor_user_root,
            projects_root=args.projects_root,
            compact=args.compact,
        )
        print(
            f"Exported {summary['session_count']} sessions to {summary['output_dir']}",
            file=sys.stderr,
        )
        return 0

    interval = max(60, args.interval)
    print(
        f"cursor-agent-memory-sync: exporting every {interval}s to {get_export_root()}",
        file=sys.stderr,
    )
    while True:
        try:
            summary = run_once(
                include_raw=include_raw,
                limit=args.limit,
                cursor_user_root=args.cursor_user_root,
                projects_root=args.projects_root,
                compact=args.compact,
            )
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{summary['session_count']} sessions -> {summary['output_dir']}",
                file=sys.stderr,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] export failed: {exc}", file=sys.stderr)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
