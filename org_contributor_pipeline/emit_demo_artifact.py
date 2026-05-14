"""Write a demo pipeline artifact (JSON) for local/CI automation — no GitLab required."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from org_contributor_pipeline.env_loader import load_repo_dotenv
from org_contributor_pipeline.models.schemas import CommitEvent, PluginResult, PluginStatus


def _commit_dict(e: CommitEvent) -> dict[str, Any]:
    return asdict(e)


def _plugin_dict(p: PluginResult) -> dict[str, Any]:
    d = asdict(p)
    d["status"] = p.status.value if isinstance(p.status, PluginStatus) else str(p.status)
    return d


def build_minimal_demo_artifact() -> dict[str, Any]:
    """Synthetic slice: two people, one repo (smallest smoke test)."""
    events = [
        CommitEvent(
            project_id="1001",
            project_path="demo/client-game",
            sha="a1b2c3d4",
            committed_at="2026-05-10T14:22:00+00:00",
            author_email="alice@example.com",
            author_name="Alice Dev",
            person_key="alice@example.com",
            insertions=120,
            deletions=15,
            files_changed=6,
            metadata={"branch": "main"},
        ),
        CommitEvent(
            project_id="1001",
            project_path="demo/client-game",
            sha="e5f6c7d8",
            committed_at="2026-05-11T09:01:00+00:00",
            author_email="bob@example.com",
            author_name="Bob Chen",
            person_key="bob@example.com",
            insertions=40,
            deletions=200,
            files_changed=22,
            metadata={"branch": "main", "note": "includes vendor path touches"},
        ),
    ]
    plugins = [
        PluginResult(
            plugin_id="path_touch_summary",
            plugin_version="0.0.1",
            person_key="alice@example.com",
            project_path="demo/client-game",
            window_start="2026-05-01T00:00:00+00:00",
            window_end="2026-05-12T23:59:59+00:00",
            status=PluginStatus.OK,
            dimension_keys=["engineering.habits", "architecture.modules"],
            metrics=[
                {"name": "game_ts_files_touched", "value": 5, "unit": "count", "confidence": "medium"},
                {"name": "largest_single_commit_insertions", "value": 80, "unit": "lines", "confidence": "high"},
            ],
            evidence=[{"kind": "commit", "sha": "a1b2c3d4", "path_hint": "assets/scripts/game/ui/"}],
            na_reason=None,
            error=None,
        ),
        PluginResult(
            plugin_id="path_touch_summary",
            plugin_version="0.0.1",
            person_key="bob@example.com",
            project_path="demo/client-game",
            window_start="2026-05-01T00:00:00+00:00",
            window_end="2026-05-12T23:59:59+00:00",
            status=PluginStatus.OK,
            dimension_keys=["engineering.habits"],
            metrics=[{"name": "game_ts_files_touched", "value": 2, "unit": "count", "confidence": "low"}],
            evidence=[{"kind": "commit", "sha": "e5f6c7d8", "path_hint": "assets/scripts/game/"}],
            na_reason=None,
            error=None,
        ),
        PluginResult(
            plugin_id="submodule_boundary_scan",
            plugin_version="0.0.1",
            person_key="bob@example.com",
            project_path="demo/client-game",
            window_start="2026-05-01T00:00:00+00:00",
            window_end="2026-05-12T23:59:59+00:00",
            status=PluginStatus.SKIPPED,
            dimension_keys=["architecture.framework"],
            metrics=[],
            evidence=[],
            na_reason="No commits touching submodule paths in window; role marked as UI-only in meta.",
            error=None,
        ),
    ]
    return {
        "artifact_version": 1,
        "meta": {
            "window_start": "2026-05-01T00:00:00+00:00",
            "window_end": "2026-05-12T23:59:59+00:00",
            "timezone": "UTC",
            "gitlab_group": "demo/example",
            "included_project_paths": ["demo/client-game"],
            "submodule_policy": "Commits in vendor/submodule paths discounted in downstream review; see plugin na_reason.",
            "mailmap_version": "demo-mailmap-v0",
            "fte_notes": {
                "alice@example.com": "1.0 FTE core feature",
                "bob@example.com": "0.5 FTE support + UI fixes",
            },
        },
        "commit_events": [_commit_dict(e) for e in events],
        "plugin_results": [_plugin_dict(p) for p in plugins],
    }


def build_full_demo_artifact() -> dict[str, Any]:
    """Five games / five primary Git authors — aligns with internal horizontal-review naming (synthetic facts)."""
    window_start = "2026-03-13T00:00:00+00:00"
    window_end = "2026-05-10T23:59:59+00:00"
    paths = [
        "proj-l-client-dndh",
        "proj-l-client-mcjb",
        "proj-l-client-mjhl",
        "proj-l-client-xjcs",
        "lei-shen-zhi-chui-client",
    ]
    rows = [
        # person_key, author_email, author_name, project_path, sha, ins, del, files, meta_note, fte
        (
            "pao@finger.demo",
            "dpunity920000@gmail.com",
            "Pao",
            "proj-l-client-dndh",
            "dndh01",
            420,
            30,
            18,
            "大闹东海 · core game loop",
            "1.0 FTE · 核心功能",
        ),
        (
            "johnny@finger.demo",
            "johnny@finger.demo",
            "Johnny",
            "proj-l-client-mcjb",
            "mcjb01",
            210,
            45,
            12,
            "喵財進寶",
            "1.0 FTE",
        ),
        (
            "ali@finger.demo",
            "ali@finger.demo",
            "劉彥辰 Ali",
            "proj-l-client-mjhl",
            "mjhl01",
            380,
            120,
            24,
            "麻將胡了 · 高 game 目录占比（演示）",
            "1.0 FTE",
        ),
        (
            "maomao@finger.demo",
            "maomao@finger.demo",
            "貓毛",
            "proj-l-client-xjcs",
            "xjcs01",
            900,
            120000,
            6988,
            "仙境傳說 · 含大型初始環境匯入（演示，须打折解读）",
            "1.0 FTE",
        ),
        (
            "jackal@finger.demo",
            "jackal0807@hotmail.com",
            "jackal",
            "lei-shen-zhi-chui-client",
            "lei01",
            150,
            90,
            11,
            "雷神之錘 · release/1.0.x 口径（演示）",
            "1.0 FTE",
        ),
    ]
    events: list[CommitEvent] = []
    for i, (pk, em, an, pp, sha, ins, dels, fc, note, _) in enumerate(rows):
        events.append(
            CommitEvent(
                project_id=f"gid-{2000 + i}",
                project_path=pp,
                sha=sha,
                committed_at="2026-05-02T10:00:00+00:00",
                author_email=em,
                author_name=an,
                person_key=pk,
                insertions=ins,
                deletions=dels,
                files_changed=fc,
                metadata={"branch": "main", "note": note},
            )
        )
        events.append(
            CommitEvent(
                project_id=f"gid-{2000 + i}",
                project_path=pp,
                sha=f"{sha}b",
                committed_at="2026-05-06T15:30:00+00:00",
                author_email=em,
                author_name=an,
                person_key=pk,
                insertions=80,
                deletions=40,
                files_changed=6,
                metadata={"branch": "main"},
            )
        )

    fte = {r[0]: r[9] for r in rows}
    cn_map = {
        "包峰華": {"person_key": "pao@finger.demo", "git_author": "Pao", "project_cn": "大鬧東海", "repo": "proj-l-client-dndh"},
        "李紳旭": {"person_key": "johnny@finger.demo", "git_author": "Johnny", "project_cn": "喵財進寶", "repo": "proj-l-client-mcjb"},
        "蕭志文": {"person_key": "ali@finger.demo", "git_author": "劉彥辰 Ali", "project_cn": "麻將胡了", "repo": "proj-l-client-mjhl"},
        "李育瑋": {"person_key": "maomao@finger.demo", "git_author": "貓毛", "project_cn": "仙境傳說", "repo": "proj-l-client-xjcs"},
        "蔡政廷": {"person_key": "jackal@finger.demo", "git_author": "jackal", "project_cn": "雷神之錘", "repo": "lei-shen-zhi-chui-client"},
    }

    plugins: list[PluginResult] = []
    touch_profiles = [
        ("pao@finger.demo", "proj-l-client-dndh", 28, 95, "high"),
        ("johnny@finger.demo", "proj-l-client-mcjb", 14, 62, "medium"),
        ("ali@finger.demo", "proj-l-client-mjhl", 40, 87, "high"),
        ("maomao@finger.demo", "proj-l-client-xjcs", 22, 55, "medium"),
        ("jackal@finger.demo", "lei-shen-zhi-chui-client", 9, 32, "low"),
    ]
    for pk, pp, touched, largest_ins, conf in touch_profiles:
        sha0 = next(e.sha for e in events if e.person_key == pk and e.project_path == pp)
        plugins.append(
            PluginResult(
                plugin_id="path_touch_summary",
                plugin_version="0.0.1",
                person_key=pk,
                project_path=pp,
                window_start=window_start,
                window_end=window_end,
                status=PluginStatus.OK,
                dimension_keys=["engineering.habits", "architecture.modules"],
                metrics=[
                    {"name": "game_ts_files_touched", "value": touched, "unit": "count", "confidence": conf},
                    {"name": "largest_single_commit_insertions", "value": largest_ins, "unit": "lines", "confidence": "high"},
                ],
                evidence=[{"kind": "commit", "sha": sha0, "path_hint": "assets/scripts/game/"}],
                na_reason=None,
                error=None,
            )
        )

    plugins.append(
        PluginResult(
            plugin_id="submodule_boundary_scan",
            plugin_version="0.0.1",
            person_key="jackal@finger.demo",
            project_path="lei-shen-zhi-chui-client",
            window_start=window_start,
            window_end=window_end,
            status=PluginStatus.SKIPPED,
            dimension_keys=["architecture.framework"],
            metrics=[],
            evidence=[],
            na_reason="Window sample: no submodule-path commits attributed in slice; cross-check release branch.",
            error=None,
        ),
    )

    return {
        "artifact_version": 1,
        "mode": "full_five_projects_synthetic",
        "meta": {
            "window_start": window_start,
            "window_end": window_end,
            "timezone": "UTC",
            "gitlab_group": "h5_game_sh_tpe/demo-synthetic",
            "included_project_paths": paths,
            "submodule_policy": "Vendor / submodule paths discounted; large scaffold imports must not count as personal architecture.",
            "mailmap_version": "synthetic-v1",
            "cn_name_to_git": cn_map,
            "fte_notes": fte,
            "notes": "Synthetic multi-repo artifact for org_contributor_pipeline AI stages; not live GitLab export.",
        },
        "commit_events": [_commit_dict(e) for e in events],
        "plugin_results": [_plugin_dict(p) for p in plugins],
    }


def main() -> int:
    load_repo_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output JSON path",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Emit five-project / five-developer synthetic slice (not minimal two-person demo).",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.output is None:
        name = "demo_pipeline_full.json" if args.full else "demo_pipeline_input.json"
        out = root / "artifacts" / "generated" / name
    else:
        out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = build_full_demo_artifact() if args.full else build_minimal_demo_artifact()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out} ({'full' if args.full else 'minimal'})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
