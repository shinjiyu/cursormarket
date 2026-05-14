"""Heuristic signals from commit ``metadata.title`` → rubric L2 proxies (low confidence)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from org_contributor_pipeline.models.schemas import CommitEvent, PluginResult, PluginStatus
from org_contributor_pipeline.plugins._serialize import plugin_result_to_row
from org_contributor_pipeline.plugins.commit_events_io import parse_commit_event_rows

PLUGIN_ID = "commit_title_signals"
PLUGIN_VERSION = "0.1.0"

SIGNAL_DEFS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "engineering_ability.cicd_release",
        "cicd",
        (" ci", "ci:", "ci/", "pipeline", "jenkins", "gitlab-ci", ".gitlab-ci", "workflow dispatch", "github actions"),
    ),
    (
        "engineering_ability.observability_debug",
        "observability",
        ("log.", "logger", "metric", "trace", "profiler", "sentry", "debug", "排错", "日志"),
    ),
    (
        "engineering_ability.quality_gates",
        "quality_gate",
        ("test", "spec", "lint", "eslint", "jest", "junit", "unittest", "单测", "测试", "覆盖率"),
    ),
    (
        "problem_solving.triage_throughput",
        "fix_like",
        ("hotfix", "crash", "revert", "patch", "修复", "崩", "异常"),
    ),
    (
        "business_understanding.game_context",
        "game_biz",
        ("留存", "付费", "转化", "运营", "活动", "投放", "roi", "关卡", "数值", "平衡"),
    ),
    (
        "collaboration.code_review_practice",
        "merge_like",
        ("merge branch", "merge remote", " merge pr", "merged in"),
    ),
]


def _title_lower(ev: CommitEvent) -> str:
    return str((ev.metadata or {}).get("title") or "").lower()


def _match_any(title: str, kws: tuple[str, ...]) -> bool:
    return any(k in title for k in kws)


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
            dimension_keys=[],
            metrics=[],
            evidence=[],
            na_reason="No commit_events in slice.",
            error=None,
        )

    n = len(events)
    titles = [_title_lower(e) for e in events]
    dim_keys: list[str] = []

    def _add_dim(key: str) -> None:
        if key and key not in dim_keys:
            dim_keys.append(key)

    first_evidence: dict[str, CommitEvent] = {}
    metrics: list[dict[str, Any]] = [
        {
            "name": "title_signal.method",
            "value": "keyword_heuristic",
            "unit": "enum",
            "confidence": "low",
            "rubric_l2": "engineering_ability",
        }
    ]

    for rubric_l2, cat, kws in SIGNAL_DEFS:
        l1 = rubric_l2.split(".", 1)[0]
        _add_dim(l1)
        _add_dim(rubric_l2)
        c = 0
        for ev, t in zip(events, titles, strict=True):
            if _match_any(t, kws):
                c += 1
                if cat not in first_evidence:
                    first_evidence[cat] = ev
        metrics.append(
            {
                "name": f"title_signal.{cat}_commit_hits",
                "value": c,
                "unit": "count",
                "confidence": "low",
                "rubric_l2": rubric_l2,
            }
        )
        metrics.append(
            {
                "name": f"title_signal.{cat}_commit_pct",
                "value": round(100.0 * c / n, 1) if n else 0.0,
                "unit": "percent",
                "confidence": "low",
                "rubric_l2": rubric_l2,
            }
        )

    evidence: list[dict[str, Any]] = []
    for cat, ev in list(first_evidence.items())[:4]:
        meta = ev.metadata or {}
        evidence.append(
            {
                "kind": "commit",
                "sha": ev.sha,
                "title": (meta.get("title") or "")[:200],
                "web_url": meta.get("web_url"),
                "signal_category": cat,
            }
        )

    return PluginResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        person_key=person_key,
        project_path=project_path,
        window_start=window_start,
        window_end=window_end,
        status=PluginStatus.OK,
        dimension_keys=dim_keys,
        metrics=metrics,
        evidence=evidence,
        na_reason=None,
        error=None,
    )


def run_commit_title_signals_on_events(
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
