"""Parse ``commit_events`` JSON rows into ``CommitEvent`` (shared by artifact plugins)."""

from __future__ import annotations

from collections.abc import Sequence

from org_contributor_pipeline.models.schemas import CommitEvent


def parse_commit_event_rows(rows: Sequence[dict]) -> list[CommitEvent]:
    out: list[CommitEvent] = []
    for r in rows:
        meta = r.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        out.append(
            CommitEvent(
                project_id=str(r.get("project_id", "")),
                project_path=str(r.get("project_path", "")),
                sha=str(r.get("sha", "")),
                committed_at=str(r.get("committed_at", "")),
                author_email=str(r.get("author_email", "")),
                author_name=str(r.get("author_name", "")),
                person_key=str(r.get("person_key", "")),
                insertions=int(r.get("insertions") or 0),
                deletions=int(r.get("deletions") or 0),
                files_changed=int(r.get("files_changed") or 0),
                metadata=meta,
            )
        )
    return out
