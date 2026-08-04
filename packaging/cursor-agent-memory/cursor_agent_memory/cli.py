from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exporter import CursorMemoryExporter
from .i18n import available_locales, env_locale, normalise, translate


def _peek_lang(argv: list[str]) -> str:
    """Find ``--lang VALUE`` or ``--lang=VALUE`` in argv before argparse runs."""
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
        prog="cursor-agent-memory",
        description=_t("cli.export.description"),
    )
    parser.add_argument(
        "--lang",
        choices=available_locales(),
        default=locale,
        help=_t("cli.lang_help"),
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help=_t("cli.export.help_output"),
    )
    parser.add_argument(
        "--cursor-user-root",
        type=Path,
        default=None,
        help=_t("cli.export.help_cursor_user_root"),
    )
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=None,
        help=_t("cli.export.help_projects_root"),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=_t("cli.export.help_limit"),
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help=_t("cli.export.help_include_raw"),
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help=_t("cli.export.help_compact"),
    )
    return parser


def main() -> int:
    argv = sys.argv[1:]
    locale = normalise(_peek_lang(argv))
    parser = build_parser(locale)
    args = parser.parse_args(argv)
    locale = normalise(args.lang)

    exporter = CursorMemoryExporter(
        output_dir=args.output,
        cursor_user_root=args.cursor_user_root,
        projects_root=args.projects_root,
        limit=args.limit,
        include_raw=args.include_raw,
        pretty=not args.compact,
    )
    summary = exporter.export()

    print(
        translate(
            "cli.export.summary",
            locale,
            sessions=summary["session_count"],
            workspaces=summary["workspace_count"],
            transcripts=summary["transcript_file_count"],
            output=summary["output_dir"],
        )
    )
    return 0
