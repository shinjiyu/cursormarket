"""Plugin protocol for org-level scan dimensions.

Plugins emit metrics and evidence for human/AI review in Cursor. They must not
encode final hire/fire or composite A/B/C/D conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from org_contributor_pipeline.models.schemas import CommitEvent, PluginResult


@dataclass
class PipelineContext:
    """Inputs passed to each plugin for one slice of work."""

    repo_root: Path
    project_path: str
    person_key: str
    window_start: str
    window_end: str
    commit_events: list[CommitEvent] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PipelinePlugin(Protocol):
    """Implement in plugins/xxx.py and register via entry points or config."""

    plugin_id: str
    plugin_version: str

    def run(self, ctx: PipelineContext) -> PluginResult:
        """Return structured metrics; use status=skipped + na_reason when not applicable."""
