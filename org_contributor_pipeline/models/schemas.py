"""Dataclasses for cross-repo pipeline I/O. Serialized to JSON in workers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PluginStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class CommitEvent:
    """Normalized commit fact (one row per commit after identity resolution)."""

    project_id: str
    project_path: str
    sha: str
    committed_at: str  # ISO-8601
    author_email: str
    author_name: str
    person_key: str  # post-mailmap stable id; may equal email
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    # Optional keys written by enrich_commit_diffs: ``commit_diff`` with truncated unified diffs per file.


@dataclass
class PluginResult:
    """Single plugin run for one (repo window × person_key) slice."""

    plugin_id: str
    plugin_version: str
    person_key: str
    project_path: str
    window_start: str
    window_end: str
    status: PluginStatus
    dimension_keys: list[str] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    na_reason: str | None = None
    error: str | None = None
