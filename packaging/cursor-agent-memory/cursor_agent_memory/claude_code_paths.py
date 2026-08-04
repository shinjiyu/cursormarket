"""Paths for Anthropic Claude Code local data (transcripts under ~/.claude)."""

from __future__ import annotations

import os
from pathlib import Path


def get_claude_data_root() -> Path:
    """Root where Claude Code stores config + application data.

    Default: ``~/.claude`` (Windows: ``%USERPROFILE%\\.claude``).
    Override with ``CLAUDE_CONFIG_DIR`` (see Claude Code docs).
    """
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude"


def get_claude_projects_root() -> Path:
    """Directory containing per-project transcript folders (``*.jsonl``)."""
    return get_claude_data_root() / "projects"
