"""Aggregate commit/plugin facts for evaluation runs (JSON-friendly dicts)."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def required_people(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Rows: {display_zh, person_key, game_zh?, ...} from meta.evaluation_scope."""
    meta = artifact.get("meta") or {}
    scope = meta.get("evaluation_scope") or {}
    out: list[dict[str, Any]] = []
    for p in scope.get("required_people") or []:
        if not isinstance(p, dict):
            continue
        disp = str(p.get("display_zh") or "")
        for pk in p.get("person_keys") or []:
            if isinstance(pk, str) and pk:
                row = {"display_zh": disp, "person_key": pk}
                if p.get("game_zh"):
                    row["game_zh"] = p.get("game_zh")
                if p.get("primary_project_path_prefix"):
                    row["primary_project_path_prefix"] = p.get("primary_project_path_prefix")
                out.append(row)
    return out


def events_for_persons(artifact: dict[str, Any], person_keys: set[str]) -> list[dict[str, Any]]:
    rows = artifact.get("commit_events") or []
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict) and r.get("person_key") in person_keys]


def aggregate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    ins = dels = 0
    projects: set[str] = set()
    days: set[str] = set()
    for r in events:
        ins += int(r.get("insertions") or 0)
        dels += int(r.get("deletions") or 0)
        pp = r.get("project_path")
        if isinstance(pp, str) and pp:
            projects.add(pp)
        ca = r.get("committed_at")
        if isinstance(ca, str) and len(ca) >= 10:
            days.add(ca[:10])
    sorted_days = sorted(days)
    return {
        "commit_rows": len(events),
        "insertions": ins,
        "deletions": dels,
        "distinct_projects": len(projects),
        "first_day": sorted_days[0] if sorted_days else "",
        "last_day": sorted_days[-1] if sorted_days else "",
    }


def diff_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    ok = trunc = 0
    suffix_counts: dict[str, int] = defaultdict(int)
    for r in events:
        meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        cd = meta.get("commit_diff")
        if not isinstance(cd, dict):
            continue
        if cd.get("status") != "ok":
            continue
        ok += 1
        if cd.get("truncated") is True:
            trunc += 1
        files = cd.get("files")
        if not isinstance(files, list):
            continue
        for f in files:
            if not isinstance(f, dict):
                continue
            path = f.get("path")
            if not isinstance(path, str) or not path:
                continue
            ext = Path(path).suffix.lower() or "(no_ext)"
            suffix_counts[ext] += 1
    top = sorted(suffix_counts.items(), key=lambda x: -x[1])[:16]
    return {
        "commit_diff_ok": ok,
        "commit_diff_truncated_commits": trunc,
        "diff_path_suffix_top": [{"suffix": s, "count": n} for s, n in top],
    }


def sum_title_signals(plugin_rows: list[dict[str, Any]], person_key: str) -> dict[str, int]:
    cats = ("cicd", "observability", "quality_gate", "fix_like", "game_biz", "merge_like")
    acc = {c: 0 for c in cats}
    for row in plugin_rows:
        if row.get("plugin_id") != "commit_title_signals" or row.get("person_key") != person_key:
            continue
        for m in row.get("metrics") or []:
            if not isinstance(m, dict):
                continue
            name = str(m.get("name") or "")
            if not name.startswith("title_signal.") or not name.endswith("_commit_hits"):
                continue
            cat = name.removeprefix("title_signal.").removesuffix("_commit_hits")
            if cat in acc:
                acc[cat] += int(m.get("value") or 0)
    return acc


def sum_path_taxonomy(plugin_rows: list[dict[str, Any]], person_key: str) -> dict[str, int]:
    acc: dict[str, int] = defaultdict(int)
    for row in plugin_rows:
        if row.get("plugin_id") != "path_taxonomy_proxy" or row.get("person_key") != person_key:
            continue
        bucket = ""
        n = 0
        for m in row.get("metrics") or []:
            if not isinstance(m, dict):
                continue
            if m.get("name") == "path_taxonomy.bucket":
                bucket = str(m.get("value") or "")
            if m.get("name") == "path_taxonomy.commit_count":
                n = int(m.get("value") or 0)
        if bucket:
            acc[bucket] += n
    return dict(sorted(acc.items(), key=lambda x: -x[1]))


def sum_delivery_vcs(plugin_rows: list[dict[str, Any]], person_key: str) -> dict[str, Any]:
    """Sum delivery_traceability footprint across (person, project_path) slices."""
    total_commits = 0
    total_days = 0
    slices = 0
    max_lines = 0
    for row in plugin_rows:
        if row.get("plugin_id") != "delivery_traceability" or row.get("person_key") != person_key:
            continue
        slices += 1
        cc = days = mx = 0
        for m in row.get("metrics") or []:
            if not isinstance(m, dict):
                continue
            if m.get("name") == "vcs_footprint.commit_count":
                cc = int(m.get("value") or 0)
            if m.get("name") == "vcs_footprint.distinct_active_days":
                days = int(m.get("value") or 0)
            if m.get("name") == "vcs_footprint.max_lines_single_commit":
                mx = int(m.get("value") or 0)
        total_commits += cc
        total_days += days
        max_lines = max(max_lines, mx)
    return {
        "delivery_slices": slices,
        "vcs_commit_count_summed": total_commits,
        "vcs_active_days_summed": total_days,
        "vcs_max_lines_single_commit": max_lines,
    }


def top_commits_by_size(events: list[dict[str, Any]], k: int = 5) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for r in events:
        meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        title = str(meta.get("title") or "")[:120]
        sha = str(r.get("sha") or "")
        pp = str(r.get("project_path") or "")
        score = int(r.get("insertions") or 0) + int(r.get("deletions") or 0)
        scored.append(
            (
                score,
                {
                    "sha": sha,
                    "project_path": pp,
                    "title": title,
                    "lines_changed": score,
                    "web_url": meta.get("web_url"),
                },
            )
        )
    scored.sort(key=lambda x: -x[0])
    return [x[1] for x in scored[:k]]


def technical_fundamentals_facts_by_person(artifact: dict[str, Any]) -> dict[str, Any]:
    people = required_people(artifact)
    pkeys = {p["person_key"] for p in people}
    events_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in events_for_persons(artifact, pkeys):
        pk = r.get("person_key")
        if isinstance(pk, str):
            events_by[pk].append(r)

    plugin_rows = artifact.get("plugin_results") or []
    if not isinstance(plugin_rows, list):
        plugin_rows = []

    rows_out: list[dict[str, Any]] = []
    for p in people:
        pk = p["person_key"]
        ev = events_by.get(pk, [])
        agg = aggregate_events(ev)
        dst = diff_stats(ev)
        row = {
            **p,
            "window_activity": agg,
            "commit_diff": dst,
            "title_signal_commit_hits": sum_title_signals(plugin_rows, pk),
            "path_taxonomy_buckets": sum_path_taxonomy(plugin_rows, pk),
            "delivery_vcs_summed": sum_delivery_vcs(plugin_rows, pk),
            "largest_commits_sample": top_commits_by_size(ev, k=5),
        }
        row["evidence_gate"] = evidence_gate_for_person(row)
        rows_out.append(row)
    return {"people": rows_out}


def evidence_gate_for_person(facts_row: dict[str, Any]) -> str:
    """
    insufficient -> next run must be full (no commits).
    partial      -> treat as 资料不够稳定打分 per product rule -> next full.
    sufficient   -> OK to treat baseline as established for incremental follow-up.
    """
    w = facts_row.get("window_activity") or {}
    commits = int(w.get("commit_rows") or 0)
    if commits <= 0:
        return "insufficient"
    diff_ok = int((facts_row.get("commit_diff") or {}).get("commit_diff_ok") or 0)
    if diff_ok >= 1 or commits >= 20:
        return "sufficient"
    return "partial"
