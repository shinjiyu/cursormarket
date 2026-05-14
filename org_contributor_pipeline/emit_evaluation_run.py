"""Emit a single ``evaluation_run.v1`` JSON: facts + mandatory L2 score placeholders + workflow policy.

Designed for web UIs. Scores (grade / narrative) are null until filled by Agent/human or merged from a baseline run.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from org_contributor_pipeline.evaluation_facts import (
    evidence_gate_for_person,
    load_json,
    technical_fundamentals_facts_by_person,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _flatten_mandatory_l2(framework: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for l1 in framework.get("mandatory_l1") or []:
        if not isinstance(l1, dict):
            continue
        l1_id = l1.get("id")
        l1_title = l1.get("title_zh")
        for l2 in l1.get("level2") or []:
            if not isinstance(l2, dict):
                continue
            out.append(
                {
                    "l1_id": l1_id,
                    "l1_title_zh": l1_title,
                    "l2_id": l2.get("id"),
                    "l2_title_zh": l2.get("title_zh"),
                    "evidence_zh": l2.get("evidence_zh"),
                }
            )
    return out


def _empty_score_cell(dim: dict[str, Any]) -> dict[str, Any]:
    return {
        "l1_id": dim["l1_id"],
        "l1_title_zh": dim["l1_title_zh"],
        "l2_id": dim["l2_id"],
        "l2_title_zh": dim["l2_title_zh"],
        "evidence_zh": dim.get("evidence_zh"),
        "grade": None,
        "confidence": None,
        "narrative_zh": None,
        "filled_by": None,
        "filled_at": None,
        "inherited_from_run_id": None,
    }


def _merge_scores_from_baseline(
    cells: list[dict[str, Any]],
    baseline_person: dict[str, Any],
    *,
    baseline_run_id: str,
) -> None:
    old_list = baseline_person.get("mandatory_l2_scores") or []
    old: dict[tuple[Any, Any], dict[str, Any]] = {}
    for x in old_list:
        if not isinstance(x, dict):
            continue
        key = (x.get("l1_id"), x.get("l2_id"))
        old[key] = x
    for c in cells:
        prev = old.get((c.get("l1_id"), c.get("l2_id")))
        if not prev or prev.get("grade") is None:
            continue
        c["grade"] = prev.get("grade")
        c["confidence"] = prev.get("confidence")
        c["narrative_zh"] = prev.get("narrative_zh")
        c["filled_by"] = prev.get("filled_by") or "inherited_baseline"
        c["filled_at"] = prev.get("filled_at")
        c["inherited_from_run_id"] = baseline_run_id


def _artifact_fingerprint(artifact: dict[str, Any], path: Path) -> str:
    meta = artifact.get("meta") or {}
    blob = json.dumps(
        {
            "path": str(path.resolve()),
            "window_start": meta.get("window_start"),
            "window_end": meta.get("window_end"),
            "ingest": meta.get("ingest"),
            "plugins_applied": meta.get("plugins_applied"),
            "commit_diff_enrich": meta.get("commit_diff_enrich"),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _slim_prior_evaluation_run(baseline: dict[str, Any]) -> dict[str, Any]:
    """Smaller attachment: scores + run metadata only (no per-person facts duplication)."""
    people_slim: list[dict[str, Any]] = []
    for p in baseline.get("people") or []:
        if not isinstance(p, dict):
            continue
        people_slim.append(
            {
                "person_key": p.get("person_key"),
                "display_zh": p.get("display_zh"),
                "evidence_gate": p.get("evidence_gate"),
                "mandatory_l2_scores": copy.deepcopy(p.get("mandatory_l2_scores") or []),
            }
        )
    return {
        "schema_version": baseline.get("schema_version"),
        "run": copy.deepcopy(baseline.get("run") or {}),
        "workflow": copy.deepcopy(baseline.get("workflow") or {}),
        "rubric": copy.deepcopy(baseline.get("rubric") or {}),
        "people": people_slim,
    }


def _prior_attachment(
    *,
    baseline_root: dict[str, Any],
    baseline_path: Path,
    embed_mode: str,
) -> dict[str, Any]:
    base = {
        "embed_mode": embed_mode,
        "baseline_source_path": str(baseline_path.resolve()),
    }
    if embed_mode == "full":
        base["document"] = copy.deepcopy(baseline_root)
    else:
        base["document"] = _slim_prior_evaluation_run(baseline_root)
    return base


def _derive_workflow(
    *,
    gates: list[str],
    run_kind_requested: str,
    baseline_present: bool,
) -> dict[str, Any]:
    """
    Product rule (user-approved):
    - If any required person is ``insufficient`` or ``partial`` for stat-layer gate,
      the **next** scoring pass should again be **full** (do not rely on incremental only).
    - Incremental is allowed only when **all** are ``sufficient``.
    """
    if any(g == "insufficient" for g in gates):
        tier = "blocked"
        next_rec = "full"
        reason_codes = ["evidence_insufficient_zero_commits"]
        reason_zh = "存在必评人员在窗口内 0 提交；下次须全量审核/打分。"
    elif any(g == "partial" for g in gates):
        tier = "weak"
        next_rec = "full"
        reason_codes = ["evidence_partial_not_enough_for_stable_scores"]
        reason_zh = "存在必评人员资料不足以稳定覆盖必审 L2（diff/体量门槛未过）；下次仍须先全量打分。"
    else:
        tier = "ok"
        next_rec = "incremental_eligible"
        reason_codes = []
        reason_zh = "事实层门槛满足；可在固定基线之上做增量提交审核并续打分。"

    coercion: dict[str, Any] = {}
    effective = run_kind_requested
    if run_kind_requested == "incremental":
        if not baseline_present:
            coercion = {
                "forced_effective_run_kind": "full",
                "reason_zh": "请求 incremental 但未提供 --baseline-json；已按 full 处理。",
            }
            effective = "full"
        elif next_rec != "incremental_eligible":
            coercion = {
                "forced_effective_run_kind": "full",
                "reason_zh": "证据门槛未满足全绿；按约定下次须全量，本 run 以 full 生效。",
            }
            effective = "full"
    return {
        "evidence_tier": tier,
        "derived_next_run_recommendation": next_rec,
        "reason_codes": reason_codes,
        "reason_zh": reason_zh,
        "run_kind_requested": run_kind_requested,
        "run_kind_effective": effective,
        "coercion": coercion or None,
    }


def build_evaluation_run(
    artifact: dict[str, Any],
    *,
    artifact_path: Path,
    run_kind: str,
    baseline_json: Path | None,
    pipeline_capability_epoch: int,
    embed_baseline: str,
) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    fw = load_json(_repo_root() / "rubric" / "review_framework.json")
    mandatory_dims = _flatten_mandatory_l2(fw)

    facts_bundle = technical_fundamentals_facts_by_person(artifact)
    baseline_root: dict[str, Any] | None = None
    baseline_run_id = ""
    if baseline_json and baseline_json.is_file():
        baseline_root = load_json(baseline_json)
        baseline_run_id = str((baseline_root.get("run") or {}).get("run_id") or "")

    baseline_by_pk: dict[str, dict[str, Any]] = {}
    if baseline_root:
        for bp in baseline_root.get("people") or []:
            if isinstance(bp, dict) and bp.get("person_key"):
                baseline_by_pk[str(bp["person_key"])] = bp

    fact_rows = [r for r in (facts_bundle.get("people") or []) if isinstance(r, dict)]
    gates: list[str] = [
        str(r.get("evidence_gate") or evidence_gate_for_person(r)) for r in fact_rows
    ]
    wf = _derive_workflow(
        gates=gates,
        run_kind_requested=run_kind,
        baseline_present=bool(baseline_json and baseline_json.is_file()),
    )
    allow_incremental_merge = (
        run_kind == "incremental"
        and bool(baseline_json and baseline_json.is_file())
        and wf.get("run_kind_effective") == "incremental"
    )

    people_out: list[dict[str, Any]] = []
    for row in fact_rows:
        pk = str(row.get("person_key") or "")
        gate = str(row.get("evidence_gate") or evidence_gate_for_person(row))

        cells = [_empty_score_cell(dict(d)) for d in mandatory_dims]
        if allow_incremental_merge and pk in baseline_by_pk and baseline_run_id:
            _merge_scores_from_baseline(cells, baseline_by_pk[pk], baseline_run_id=baseline_run_id)

        facts_only = {
            k: v
            for k, v in row.items()
            if k
            not in (
                "display_zh",
                "person_key",
                "game_zh",
                "primary_project_path_prefix",
                "evidence_gate",
            )
        }

        people_out.append(
            {
                "display_zh": row.get("display_zh"),
                "person_key": pk,
                "game_zh": row.get("game_zh"),
                "primary_project_path_prefix": row.get("primary_project_path_prefix"),
                "evidence_gate": gate,
                "facts": facts_only,
                "mandatory_l2_scores": cells,
            }
        )

    meta = artifact.get("meta") or {}
    out: dict[str, Any] = {
        "schema_version": "evaluation_run.v1",
        "run": {
            "run_id": run_id,
            "created_at": created,
            "run_kind_requested": run_kind,
            "run_kind_effective": wf["run_kind_effective"],
            "baseline_run_id": baseline_run_id or None,
            "pipeline_capability_epoch": pipeline_capability_epoch,
            "artifact_path": str(artifact_path.resolve()),
            "artifact_fingerprint": _artifact_fingerprint(artifact, artifact_path),
            "window_start": meta.get("window_start"),
            "window_end": meta.get("window_end"),
            "gitlab_group": meta.get("gitlab_group"),
            "ingest": meta.get("ingest"),
            "plugins_applied": meta.get("plugins_applied"),
        },
        "workflow": {
            "version": 1,
            "description_zh": (
                "新增考核能力或更换 rubric/插件世代 → 对项目做一次全量审核并打底分；"
                "之后在同一基线上可对增量提交续打分。"
                "若当前资料不足以稳定打分（证据门槛未全绿），下一次须先全量，不要只做增量。"
            ),
            "triggers_full_rescore_zh": [
                "pipeline_capability_epoch 递增（新插件/新 ingest 口径）",
                "evaluation_scope / mailmap 变更",
                "artifact 时间窗大幅变更",
                "workflow.derived_next_run_recommendation 为 full（证据不足或 partial）",
            ],
            "incremental_merge": {
                "uses_baseline_json": bool(baseline_json),
                "applied": allow_incremental_merge,
                "copies_non_null_grades": True,
                "facts_always_from_current_artifact": True,
                "includes_prior_attachment": bool(
                    baseline_root is not None
                    and embed_baseline in ("full", "scores")
                    and baseline_json is not None
                ),
            },
            **{k: v for k, v in wf.items() if k not in ("run_kind_requested", "run_kind_effective")},
        },
        "rubric": {
            "review_framework_schema_version": fw.get("schema_version"),
            "review_framework_title_zh": fw.get("title_zh"),
            "mandatory_l2_count": len(mandatory_dims),
            "mandatory_l2_dimensions": mandatory_dims,
        },
        "people": people_out,
    }

    if baseline_root is not None and embed_baseline in ("full", "scores") and baseline_json is not None:
        out["prior_evaluation_run_attachment"] = _prior_attachment(
            baseline_root=baseline_root,
            baseline_path=baseline_json,
            embed_mode=embed_baseline,
        )

    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True, help="Enriched artifact JSON")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output evaluation_run.json")
    p.add_argument(
        "--run-kind",
        choices=("full", "incremental"),
        default="full",
        help="incremental requires --baseline-json with a prior evaluation_run.v1",
    )
    p.add_argument(
        "--baseline-json",
        type=Path,
        default=None,
        help="Prior evaluation_run.v1 to inherit non-null grades (incremental)",
    )
    p.add_argument(
        "--pipeline-capability-epoch",
        type=int,
        default=1,
        help="Bump when you ship new scoring plugins/prompts to force full-rescore semantics downstream",
    )
    p.add_argument(
        "--embed-baseline",
        choices=("none", "scores", "full", "auto"),
        default="auto",
        help="auto: attach full prior JSON when incremental+baseline; scores: slim prior; none: omit",
    )
    args = p.parse_args()

    if args.run_kind == "incremental" and not args.baseline_json:
        p.error("incremental requires --baseline-json")

    embed = args.embed_baseline
    if embed == "auto":
        embed = "full" if (args.run_kind == "incremental" and args.baseline_json) else "none"
    if embed in ("full", "scores") and not args.baseline_json:
        p.error("--embed-baseline full|scores requires --baseline-json")

    art = load_json(args.input)
    payload = build_evaluation_run(
        art,
        artifact_path=args.input,
        run_kind=args.run_kind,
        baseline_json=args.baseline_json,
        pipeline_capability_epoch=args.pipeline_capability_epoch,
        embed_baseline=embed,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {args.output} run_id={payload['run']['run_id']} "
        f"effective={payload['run']['run_kind_effective']} "
        f"prior_attachment={'prior_evaluation_run_attachment' in payload}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
