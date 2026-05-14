"""Classify ``project_path`` into coarse buckets (architecture-touch proxy, low confidence)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from org_contributor_pipeline.models.schemas import CommitEvent, PluginResult, PluginStatus
from org_contributor_pipeline.plugins._serialize import plugin_result_to_row
from org_contributor_pipeline.plugins.commit_events_io import parse_commit_event_rows

PLUGIN_ID = "path_taxonomy_proxy"
PLUGIN_VERSION = "0.1.0"

L1 = "system_design"
L2 = f"{L1}.architecture_boundaries"
DIMENSION_KEYS = [L1, L2]


def classify_project_path(project_path: str) -> str:
    p = project_path.lower().replace("\\", "/")
    if "common" in p or "project-l-common" in p or "artcommon" in p:
        return "common_or_shared_stack"
    if "extension-tools" in p or "extension_tools" in p:
        return "extension_tools"
    if "genbot" in p:
        return "genbot_or_tooling"
    if "artwork" in p or "art-" in p:
        return "art_or_asset_pipeline"
    if "client" in p or "proj-l-client" in p:
        return "game_client_repo"
    return "other_or_unknown"


def build_row_for_slice(
    *,
    person_key: str,
    project_path: str,
    window_start: str,
    window_end: str,
    events: Sequence[CommitEvent],
) -> PluginResult:
    if not events:
        return PluginResult(
            plugin_id=PLUGIN_ID,
            plugin_version=PLUGIN_VERSION,
            person_key=person_key,
            project_path=project_path,
            window_start=window_start,
            window_end=window_end,
            status=PluginStatus.SKIPPED,
            dimension_keys=DIMENSION_KEYS,
            metrics=[],
            evidence=[],
            na_reason="No commit_events in slice.",
            error=None,
        )

    bucket = classify_project_path(project_path)
    n = len(events)
    metrics: list[dict[str, Any]] = [
        {
            "name": "path_taxonomy.bucket",
            "value": bucket,
            "unit": "enum",
            "confidence": "low",
            "rubric_l2": L2,
        },
        {
            "name": "path_taxonomy.commit_count",
            "value": n,
            "unit": "count",
            "confidence": "high",
            "rubric_l2": L2,
        },
        {
            "name": "path_taxonomy.disclaimer",
            "value": "path_only_proxy_not_architecture_review",
            "unit": "enum",
            "confidence": "low",
            "rubric_l2": L2,
        },
    ]
    top = events[0]
    tmeta = top.metadata or {}
    evidence = [
        {
            "kind": "commit",
            "sha": top.sha,
            "title": (tmeta.get("title") or "")[:120],
            "project_path": project_path,
            "path_bucket": bucket,
        }
    ]
    return PluginResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        person_key=person_key,
        project_path=project_path,
        window_start=window_start,
        window_end=window_end,
        status=PluginStatus.OK,
        dimension_keys=DIMENSION_KEYS,
        metrics=metrics,
        evidence=evidence,
        na_reason=None,
        error=None,
    )


def run_path_taxonomy_on_events(
    *,
    commit_events: Sequence[dict],
    window_start: str,
    window_end: str,
) -> list[dict[str, Any]]:
    events = parse_commit_event_rows(commit_events)
    buckets: dict[tuple[str, str], list[CommitEvent]] = defaultdict(list)
    for e in events:
        buckets[(e.person_key, e.project_path)].append(e)
    out: list[dict[str, Any]] = []
    for (pk, pp), evs in sorted(buckets.items()):
        pr = build_row_for_slice(
            person_key=pk,
            project_path=pp,
            window_start=window_start,
            window_end=window_end,
            events=evs,
        )
        out.append(plugin_result_to_row(pr))
    return out
