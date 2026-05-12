from __future__ import annotations

import argparse
from pathlib import Path

from .exporter import CursorMemoryExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cursor-agent-memory",
        description="Extract local Cursor sessions into agent-friendly JSON.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory where extracted files will be written.",
    )
    parser.add_argument(
        "--cursor-user-root",
        type=Path,
        default=None,
        help="Override the Cursor User directory. Defaults to %%APPDATA%%\\Cursor\\User.",
    )
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=None,
        help="Override the .cursor projects directory. Defaults to %%USERPROFILE%%\\.cursor\\projects.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only export the most recently updated N sessions.",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Also write raw transcript files and raw session payloads.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write compact JSON instead of pretty printed files.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

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
        "Exported "
        f"{summary['session_count']} sessions, "
        f"{summary['workspace_count']} workspaces, "
        f"and {summary['transcript_file_count']} transcript files "
        f"to {summary['output_dir']}"
    )
    return 0
