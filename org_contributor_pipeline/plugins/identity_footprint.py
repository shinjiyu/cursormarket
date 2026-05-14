"""Per-person commit volume & stable identity flag (``unknown:*`` shards)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from org_contributor_pipeline.models.schemas import CommitEvent, PluginResult, PluginStatus
from org_contributor_pipeline.plugins._serialize import plugin_result_to_row
from org_contributor_pipeline.plugins.commit_events_io import parse_commit_event_rows

PLUGIN_ID = "identity_footprint"
PLUGIN_VERSION = "0.1.0"

# Cross-cutting: affects confidence of all person-scoped dimensions
DIMENSION_KEYS: list[str] = []


def _is_unknown_shard(person_key: str) -> bool:
    return person_key.startswith("unknown:")


def build_row_for_person(
    *,
    person_key: str,
    window_start: str,
    window_end: str,
    events: Sequence[CommitEvent],
) -> PluginResult:
    if not events:
        return PluginResult(
            plugin_id=PLUGIN_ID,
            plugin_version=PLUGIN_VERSION,
            person_key=person_key,
            project_path="*",
            window_start=window_start,
            window_end=window_end,
            status=PluginStatus.SKIPPED,
            dimension_keys=DIMENSION_KEYS,
            metrics=[],
            evidence=[],
            na_reason="No commits for this person_key.",
            error=None,
        )

    n = len(events)
    projects = {e.project_path for e in events if e.project_path}
    stable = not _is_unknown_shard(person_key)
    dates = sorted({e.committed_at[:10] for e in events if e.committed_at})

    metrics: list[dict[str, Any]] = [
        {
            "name": "identity.is_unknown_shard",
            "value": not stable,
            "unit": "bool",
            "confidence": "high",
            "rubric_l2": "meta",
        },
        {
            "name": "identity.stable_person_key",
            "value": stable,
            "unit": "bool",
            "confidence": "high",
            "rubric_l2": "meta",
        },
        {
            "name": "identity.commit_rows_in_window",
            "value": n,
            "unit": "count",
            "confidence": "high",
            "rubric_l2": "meta",
        },
        {
            "name": "identity.distinct_projects",
            "value": len(projects),
            "unit": "count",
            "confidence": "high",
            "rubric_l2": "meta",
        },
        {
            "name": "identity.first_commit_day",
            "value": dates[0] if dates else "",
            "unit": "date",
            "confidence": "medium",
            "rubric_l2": "meta",
        },
        {
            "name": "identity.last_commit_day",
            "value": dates[-1] if dates else "",
            "unit": "date",
            "confidence": "medium",
            "rubric_l2": "meta",
        },
    ]
    ev = events[0]
    evidence = [
        {
            "kind": "person_aggregate",
            "person_key": person_key,
            "sample_sha": ev.sha,
            "sample_project_path": ev.project_path,
        }
    ]
    return PluginResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        person_key=person_key,
        project_path="*",
        window_start=window_start,
        window_end=window_end,
        status=PluginStatus.OK,
        dimension_keys=DIMENSION_KEYS,
        metrics=metrics,
        evidence=evidence,
        na_reason=None,
        error=None,
    )


def run_identity_footprint_on_events(
    *,
    commit_events: Sequence[dict],
    window_start: str,
    window_end: str,
) -> list[dict[str, Any]]:
    events = parse_commit_event_rows(commit_events)
    by_person: dict[str, list[CommitEvent]] = defaultdict(list)
    for e in events:
        by_person[e.person_key].append(e)
    out: list[dict[str, Any]] = []
    for pk, evs in sorted(by_person.items()):
        pr = build_row_for_person(person_key=pk, window_start=window_start, window_end=window_end, events=evs)
        out.append(plugin_result_to_row(pr))
    return out
