"""MCP server: expose scheduled Cursor session exports to Cursor (cross-workspace log access)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .exporter import safe_name
from .paths import get_export_root

mcp = FastMCP(
    "cursor-agent-memory-logs",
    instructions=(
        "Local-first cross-workspace Cursor session memory. "
        "Reads exports from CURSOR_AGENT_MEMORY_EXPORT_DIR "
        "(default ~/.cursor-agent-memory/export). "
        "If tools report missing manifest/index, run: "
        "uvx --from git+https://github.com/shinjiyu/cursormarket.git"
        "#subdirectory=packaging/cursor-agent-memory cursor-agent-memory-sync --once. "
        "Then list, search, or get sessions to recover prior chats from other workspaces."
    ),
)


def _export_root() -> Path:
    return get_export_root()


def _manifest_path() -> Path:
    return _export_root() / "manifest.json"


def _session_index_path() -> Path:
    return _export_root() / "normalized" / "session_index.json"


def _sessions_dir() -> Path:
    return _export_root() / "normalized" / "sessions"


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return json.load(handle)


@mcp.tool()
def cursor_logs_export_dir() -> str:
    """Return the absolute path where sync exports are written (CURSOR_AGENT_MEMORY_EXPORT_DIR)."""
    return str(_export_root().resolve())


@mcp.tool()
def cursor_logs_read_manifest() -> str:
    """Read export manifest.json (session counts, paths, generated time). Returns JSON or an error message."""
    path = _manifest_path()
    data = _read_json(path)
    if data is None:
        return json.dumps(
            {
                "error": "manifest_not_found",
                "hint": "Run: python -m cursor_agent_memory.sync_daemon --once",
                "expected_path": str(path),
            },
            ensure_ascii=False,
        )
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def cursor_logs_list_sessions(limit: int = 50) -> str:
    """List recent sessions from session_index.json (title, workspace, updated_at, tools_used)."""
    path = _session_index_path()
    data = _read_json(path)
    if data is None:
        return json.dumps(
            {
                "error": "session_index_not_found",
                "hint": "Run sync export first: python -m cursor_agent_memory.sync_daemon --once",
                "expected_path": str(path),
            },
            ensure_ascii=False,
        )
    if not isinstance(data, list):
        return json.dumps({"error": "invalid_session_index"}, ensure_ascii=False)
    trimmed = data[: max(1, min(limit, 500))]
    return json.dumps(trimmed, ensure_ascii=False, indent=2)


@mcp.tool()
def cursor_logs_search_sessions(query: str, limit: int = 30) -> str:
    """Search session_index by substring in title, session_id, or workspace_paths (case-insensitive)."""
    path = _session_index_path()
    data = _read_json(path)
    if data is None:
        return json.dumps({"error": "session_index_not_found", "path": str(path)}, ensure_ascii=False)
    if not isinstance(data, list):
        return json.dumps({"error": "invalid_session_index"}, ensure_ascii=False)
    q = query.lower()
    matches: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        hay = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("session_id", "")),
                " ".join(item.get("workspace_paths") or []),
            ]
        ).lower()
        if q in hay:
            matches.append(item)
        if len(matches) >= max(1, min(limit, 200)):
            break
    return json.dumps(matches, ensure_ascii=False, indent=2)


@mcp.tool()
def cursor_logs_get_session(session_id: str, max_chars: int = 120000) -> str:
    """Load one normalized session JSON by session_id. Large payloads are truncated with a notice."""
    root = _sessions_dir()
    candidate = root / f"{safe_name(session_id)}.json"
    if not candidate.exists():
        for path in root.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    blob = json.load(handle)
                if blob.get("session_id") == session_id:
                    candidate = path
                    break
            except (OSError, json.JSONDecodeError):
                continue
    if not candidate.exists():
        return json.dumps(
            {
                "error": "session_not_found",
                "session_id": session_id,
                "searched_dir": str(root),
            },
            ensure_ascii=False,
        )
    text = candidate.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    head = text[:max_chars]
    return head + f"\n\n... truncated, total_chars={len(text)}, max_chars={max_chars}"


@mcp.tool()
def cursor_logs_read_workspaces() -> str:
    """Read normalized/workspaces.json if present."""
    path = _export_root() / "normalized" / "workspaces.json"
    data = _read_json(path)
    if data is None:
        return json.dumps({"error": "workspaces_not_found", "path": str(path)}, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False, indent=2)


def main() -> None:
    # Optional: reduce noise when Cursor spawns the server
    if os.environ.get("CURSOR_AGENT_MEMORY_MCP_QUIET", "").lower() in ("1", "true", "yes"):
        import logging

        logging.getLogger("mcp").setLevel(logging.WARNING)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
