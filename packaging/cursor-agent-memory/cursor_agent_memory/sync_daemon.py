"""Periodic export of local Cursor sessions to a fixed directory (for MCP / cross-workspace use)."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .exporter import CursorMemoryExporter
from .i18n import available_locales, env_locale, normalise, translate
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


def _peek_lang(argv: list[str]) -> str:
    for index, token in enumerate(argv):
        if token == "--lang" and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith("--lang="):
            return token.split("=", 1)[1]
    return env_locale()


def build_parser(locale: str) -> argparse.ArgumentParser:
    def _t(key: str) -> str:
        return translate(key, locale)

    parser = argparse.ArgumentParser(
        prog="cursor-agent-memory-sync",
        description=_t("cli.sync.description"),
    )
    parser.add_argument(
        "--lang",
        choices=available_locales(),
        default=locale,
        help=_t("cli.lang_help"),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help=_t("cli.sync.help_once"),
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("CURSOR_AGENT_MEMORY_SYNC_INTERVAL_SECONDS", "3600")),
        help=_t("cli.sync.help_interval"),
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help=_t("cli.sync.help_include_raw"),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=_t("cli.sync.help_limit"),
    )
    parser.add_argument("--cursor-user-root", type=Path, default=None)
    parser.add_argument("--projects-root", type=Path, default=None)
    parser.add_argument("--compact", action="store_true")
    return parser


def main() -> int:
    argv = sys.argv[1:]
    locale = normalise(_peek_lang(argv))
    parser = build_parser(locale)
    args = parser.parse_args(argv)
    locale = normalise(args.lang)

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
            translate(
                "cli.sync.summary_once",
                locale,
                sessions=summary["session_count"],
                output=summary["output_dir"],
            ),
            file=sys.stderr,
        )
        return 0

    interval = max(60, args.interval)
    print(
        translate(
            "cli.sync.loop_start",
            locale,
            interval=interval,
            output=get_export_root(),
        ),
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
                translate(
                    "cli.sync.loop_iter",
                    locale,
                    ts=time.strftime("%Y-%m-%d %H:%M:%S"),
                    sessions=summary["session_count"],
                    output=summary["output_dir"],
                ),
                file=sys.stderr,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                translate(
                    "cli.sync.loop_failed",
                    locale,
                    ts=time.strftime("%Y-%m-%d %H:%M:%S"),
                    error=exc,
                ),
                file=sys.stderr,
            )
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
