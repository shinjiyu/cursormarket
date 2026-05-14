"""L1「工程能力」下 Git 代理子项 ``vcs_footprint``：仅从 ``commit_events`` 聚合。

产出 ``PluginResult`` 切片：每个 (person_key, project_path) 一行；``dimension_keys``
与 ``rubric/dimensions.json`` 中 ``engineering_ability`` / ``vcs_footprint`` 对齐。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from org_contributor_pipeline.models.schemas import CommitEvent, PluginResult, PluginStatus
from org_contributor_pipeline.plugins._serialize import plugin_result_to_row
from org_contributor_pipeline.plugins.base import PipelineContext
from org_contributor_pipeline.plugins.commit_events_io import parse_commit_event_rows

PLUGIN_ID = "delivery_traceability"
PLUGIN_VERSION = "0.1.0"

L1 = "engineering_ability"
L2_VCS = f"{L1}.vcs_footprint"
DIMENSION_KEYS = [L1, L2_VCS]


def _committed_day(iso: str) -> str:
    if not iso:
        return ""
    return iso[:10]


def build_plugin_result_for_slice(
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
            na_reason="No commit_events in this (person_key, project_path) slice.",
            error=None,
        )

    n = len(events)
    days = {_committed_day(e.committed_at) for e in events if _committed_day(e.committed_at)}
    active_days = len(days)
    with_title = sum(1 for e in events if (e.metadata.get("title") or "").strip())
    with_url = sum(1 for e in events if (e.metadata.get("web_url") or "").strip())
    total_ins = sum(e.insertions for e in events)
    total_del = sum(e.deletions for e in events)
    per_lines = [e.insertions + e.deletions for e in events]
    max_lines = max(per_lines) if per_lines else 0
    max_idx = per_lines.index(max_lines) if per_lines else 0
    top = events[max_idx]

    pct_title = round(100.0 * with_title / n, 1) if n else 0.0
    pct_url = round(100.0 * with_url / n, 1) if n else 0.0
    cpad = round(n / active_days, 2) if active_days else float(n)

    metrics: list[dict[str, Any]] = [
        {
            "name": "vcs_footprint.commit_count",
            "value": n,
            "unit": "count",
            "confidence": "high",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.distinct_active_days",
            "value": active_days,
            "unit": "days",
            "confidence": "high",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.commits_per_active_day",
            "value": cpad,
            "unit": "ratio",
            "confidence": "medium",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.pct_commits_with_title",
            "value": pct_title,
            "unit": "percent",
            "confidence": "high",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.pct_commits_with_web_url",
            "value": pct_url,
            "unit": "percent",
            "confidence": "high",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.total_insertions",
            "value": total_ins,
            "unit": "lines",
            "confidence": "medium",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.total_deletions",
            "value": total_del,
            "unit": "lines",
            "confidence": "medium",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.max_lines_single_commit",
            "value": max_lines,
            "unit": "lines",
            "confidence": "medium",
            "rubric_l2": L2_VCS,
        },
        {
            "name": "vcs_footprint.slice_project_path",
            "value": project_path,
            "unit": "path",
            "confidence": "high",
            "rubric_l2": L2_VCS,
        },
    ]

    evidence: list[dict[str, Any]] = [
        {
            "kind": "commit",
            "sha": top.sha,
            "title": (top.metadata.get("title") or "")[:200],
            "web_url": top.metadata.get("web_url"),
            "note": "largest insertions+deletions in this slice",
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


def run_delivery_traceability_on_events(
    *,
    commit_events: Sequence[dict],
    window_start: str,
    window_end: str,
) -> list[dict[str, Any]]:
    events = parse_commit_event_rows(commit_events)
    buckets: dict[tuple[str, str], list[CommitEvent]] = {}
    for e in events:
        buckets.setdefault((e.person_key, e.project_path), []).append(e)

    results: list[PluginResult] = []
    for (pk, pp), evs in sorted(buckets.items()):
        pr = build_plugin_result_for_slice(
            person_key=pk,
            project_path=pp,
            window_start=window_start,
            window_end=window_end,
            events=evs,
        )
        results.append(plugin_result_to_row(pr))
    return results


class DeliveryTraceabilityPlugin:
    """Orchestrator-friendly entry (local repo_root unused for v0)."""

    plugin_id = PLUGIN_ID
    plugin_version = PLUGIN_VERSION

    def run(self, ctx: PipelineContext) -> PluginResult:
        return build_plugin_result_for_slice(
            person_key=ctx.person_key,
            project_path=ctx.project_path,
            window_start=ctx.window_start,
            window_end=ctx.window_end,
            events=ctx.commit_events,
        )

