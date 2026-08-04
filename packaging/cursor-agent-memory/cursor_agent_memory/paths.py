"""Shared paths for sync daemon and MCP server."""

from __future__ import annotations

import os
from pathlib import Path


def get_export_root() -> Path:
    """Directory where scheduled exports are written (same tree as CLI --output)."""
    default = Path.home() / ".cursor-agent-memory" / "export"
    return Path(os.environ.get("CURSOR_AGENT_MEMORY_EXPORT_DIR", str(default))).expanduser()
