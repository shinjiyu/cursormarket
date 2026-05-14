"""End-to-end demo of cursor-agent-memory without touching your real Cursor data.

What this does:

1. Builds a small synthetic export tree under ``examples/demo-export/`` that
   has the same shape as a real ``cursor-agent-memory-sync`` output.
2. Points the MCP tools at that fake tree (via ``CURSOR_AGENT_MEMORY_EXPORT_DIR``).
3. Calls each tool the way Cursor's agent would, and prints the result.

Run:

    python -m examples.run_demo

Then read the printed output to see exactly the JSON shape that ``@`` -> MCP
-> ``cursor-agent-memory-logs`` would return inside Cursor.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEMO_ROOT = ROOT / "demo-export"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_session(
    session_id: str,
    title: str,
    workspace_path: str,
    tools_used: list[str],
    first_user_message: str,
    snippets: list[str],
) -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "schema_version": 1,
        "session_id": session_id,
        "title": title,
        "mode": "agent",
        "model_name": "claude-sonnet-4",
        "created_at_ms": now_ms - 86_400_000,
        "updated_at_ms": now_ms - 3_600_000,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "source_kinds": ["global_sqlite", "agent_transcript"],
        "workspaces": [
            {
                "workspace_id": "demo-ws-1",
                "local_path": workspace_path,
                "workspace_uri": f"file:///{workspace_path.replace(chr(92), '/')}",
            }
        ],
        "message_count": 1 + len(snippets),
        "messages": [
            {
                "order": 0,
                "bubble_id": f"{session_id}-msg-0",
                "role": "user",
                "type": "text",
                "text": first_user_message,
                "tool_results": [],
                "summary": first_user_message[:120],
            }
        ]
        + [
            {
                "order": i + 1,
                "bubble_id": f"{session_id}-msg-{i + 1}",
                "role": "assistant",
                "type": "text",
                "text": snippet,
                "tool_results": [],
                "summary": snippet[:120],
            }
            for i, snippet in enumerate(snippets)
        ],
        "tool_events": [
            {
                "source": "sqlite",
                "tool_name": tool,
                "status": "ok",
                "path": None,
                "summary": f"called {tool}",
                "payload": {},
            }
            for tool in tools_used
        ],
        "tools_used": tools_used,
        "touched_files": [],
        "first_user_message": first_user_message,
        "checkpoints": [],
        "request_contexts": [],
        "context": None,
        "transcript_files": [],
        "transcript_event_count": 0,
    }


SESSIONS = [
    _build_session(
        session_id="demo-001-websocket-reconnect",
        title="Debug websocket reconnect loop",
        workspace_path="C:\\code\\realtime-app",
        tools_used=["Grep", "Read", "Edit"],
        first_user_message=(
            "Our websocket client keeps reconnecting in a loop after the "
            "server closes the connection cleanly. Help me find the cause."
        ),
        snippets=[
            "Looked at src/transport/websocket.ts; the close handler "
            "schedules a reconnect even on graceful close.",
            "Fix: branch on event.wasClean and skip the backoff timer.",
        ],
    ),
    _build_session(
        session_id="demo-002-pyproject-cleanup",
        title="Split monorepo pyproject into per-package",
        workspace_path="C:\\code\\internal-tools",
        tools_used=["Read", "Write", "Shell"],
        first_user_message=(
            "Move the publishable package out of the monorepo pyproject so "
            "we can ship it to PyPI without dragging the internal pipeline."
        ),
        snippets=[
            "Created packaging/<pkg>/pyproject.toml with focused metadata.",
            "Added a publish.ps1/sh that stages source + README + LICENSE "
            "into the packaging dir then runs `python -m build`.",
        ],
    ),
    _build_session(
        session_id="demo-003-i18n-locales",
        title="Wire JSON locales into web app",
        workspace_path="C:\\code\\internal-tools",
        tools_used=["Read", "Write"],
        first_user_message=(
            "Add multi-language support to the FastAPI web app, default to "
            "English, with a per-request override."
        ),
        snippets=[
            "Lookup priority: ?lang=  >  session  >  env  >  Accept-Language  >  default.",
            "Templates expose t() that falls back to en when a key is missing.",
        ],
    ),
]

WORKSPACES = [
    {
        "workspace_id": "demo-ws-1",
        "workspace_dir": "C:\\Users\\demo\\AppData\\Roaming\\Cursor\\User\\workspaceStorage\\demo-ws-1",
        "workspace_uri": "file:///C:/code/realtime-app",
        "local_path": "C:\\code\\realtime-app",
        "discovered_session_refs": ["demo-001-websocket-reconnect"],
    },
    {
        "workspace_id": "demo-ws-2",
        "workspace_dir": "C:\\Users\\demo\\AppData\\Roaming\\Cursor\\User\\workspaceStorage\\demo-ws-2",
        "workspace_uri": "file:///C:/code/internal-tools",
        "local_path": "C:\\code\\internal-tools",
        "discovered_session_refs": [
            "demo-002-pyproject-cleanup",
            "demo-003-i18n-locales",
        ],
    },
]


def materialize_demo(target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    sessions_dir = target / "normalized" / "sessions"
    sessions_dir.mkdir(parents=True)

    (target / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": _now_iso(),
                "cursor_user_root": "<demo>",
                "projects_root": "<demo>",
                "session_count": len(SESSIONS),
                "workspace_count": len(WORKSPACES),
                "transcript_file_count": 0,
                "discovered_transcript_file_count": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (target / "normalized" / "workspaces.json").write_text(
        json.dumps(WORKSPACES, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    (target / "normalized" / "session_index.json").write_text(
        json.dumps(
            [
                {
                    "session_id": s["session_id"],
                    "title": s["title"],
                    "workspace_paths": [
                        item.get("local_path") for item in s.get("workspaces", [])
                    ],
                    "updated_at": s["updated_at"],
                    "message_count": s["message_count"],
                    "tools_used": s["tools_used"],
                    "source_kinds": s["source_kinds"],
                }
                for s in SESSIONS
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    for session in SESSIONS:
        (sessions_dir / f"{session['session_id']}.json").write_text(
            json.dumps(session, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def truncate(text: str, max_chars: int = 800) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, total_chars={len(text)}]"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    print(f"Building synthetic export tree at: {DEMO_ROOT}")
    materialize_demo(DEMO_ROOT)
    os.environ["CURSOR_AGENT_MEMORY_EXPORT_DIR"] = str(DEMO_ROOT)

    # Import after the env var is set so the MCP module sees the demo path.
    from cursor_agent_memory import mcp_server as mcp

    section("cursor_logs_export_dir()")
    print(mcp.cursor_logs_export_dir())

    section("cursor_logs_read_manifest()")
    print(mcp.cursor_logs_read_manifest())

    section("cursor_logs_read_workspaces()")
    print(mcp.cursor_logs_read_workspaces())

    section("cursor_logs_list_sessions(limit=10)")
    print(mcp.cursor_logs_list_sessions(limit=10))

    section('cursor_logs_search_sessions("websocket")')
    print(mcp.cursor_logs_search_sessions("websocket"))

    section('cursor_logs_get_session("demo-001-websocket-reconnect")')
    print(truncate(mcp.cursor_logs_get_session("demo-001-websocket-reconnect")))

    print()
    print("Done. The same calls happen inside Cursor when its agent talks to")
    print("the MCP server. To use the real thing against your own Cursor data:")
    print("    1. cursor-agent-memory-sync --once")
    print("    2. add the snippet from README.md to ~/.cursor/mcp.json")
    print("    3. restart Cursor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
