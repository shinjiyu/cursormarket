"""Render ``evaluation_run.v1`` (especially ``*-scored.json``) into a readable Markdown report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _esc(s: object) -> str:
    t = "" if s is None else str(s)
    return t.replace("|", "\\|").replace("\n", " ")


def _facts_table(facts: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    wa = facts.get("window_activity") or {}
    if isinstance(wa, dict) and wa:
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        for k in ("commit_rows", "insertions", "deletions", "distinct_projects", "first_day", "last_day"):
            if k in wa:
                lines.append(f"| {k} | {_esc(wa.get(k))} |")
        lines.append("")
    cd = facts.get("commit_diff") or {}
    if isinstance(cd, dict):
        lines.append("| commit_diff | 值 |")
        lines.append("|-------------|-----|")
        lines.append(f"| commit_diff_ok | {_esc(cd.get('commit_diff_ok'))} |")
        lines.append("")
    tsh = facts.get("title_signal_commit_hits") or {}
    if isinstance(tsh, dict) and tsh:
        lines.append("| title_signal_commit_hits | 值 |")
        lines.append("|----------------------------|-----|")
        for k, v in sorted(tsh.items(), key=lambda x: str(x[0])):
            lines.append(f"| {k} | {_esc(v)} |")
        lines.append("")
    dvs = facts.get("delivery_vcs_summed") or {}
    if isinstance(dvs, dict) and dvs:
        lines.append("| delivery_vcs_summed | 值 |")
        lines.append("|---------------------|-----|")
        for k, v in sorted(dvs.items(), key=lambda x: str(x[0])):
            lines.append(f"| {k} | {_esc(v)} |")
        lines.append("")
    return lines


def _person_section(p: dict[str, Any]) -> list[str]:
    out: list[str] = []
    disp = _esc(p.get("display_zh"))
    pk = _esc(p.get("person_key"))
    out.append(f"## {disp}")
    out.append("")
    out.append("| 字段 | 值 |")
    out.append("|------|-----|")
    out.append(f"| person_key | {pk} |")
    for k in ("game_zh", "primary_project_path_prefix", "evidence_gate"):
        if p.get(k) is not None:
            out.append(f"| {k} | {_esc(p.get(k))} |")
    out.append("")
    facts = p.get("facts") or {}
    if isinstance(facts, dict):
        out.append("### 事实摘要（facts）")
        out.append("")
        out.extend(_facts_table(facts))
    scores = p.get("mandatory_l2_scores") or []
    if isinstance(scores, list) and scores:
        out.append("### 必审 L2")
        out.append("")
        out.append("| L1 | L2 | grade | confidence | narrative_zh | filled_by |")
        out.append("|----|-----|-------|------------|--------------|-----------|")
        for c in scores:
            if not isinstance(c, dict):
                continue
            out.append(
                "| "
                + _esc(c.get("l1_title_zh"))
                + " | "
                + _esc(c.get("l2_title_zh"))
                + " | "
                + _esc(c.get("grade"))
                + " | "
                + _esc(c.get("confidence"))
                + " | "
                + _esc(c.get("narrative_zh"))
                + " | "
                + _esc(c.get("filled_by"))
                + " |"
            )
        out.append("")
    return out


def render_markdown(doc: dict[str, Any], *, source_path: str) -> str:
    parts: list[str] = []
    parts.append("# evaluation_run 评审报告（Markdown）")
    parts.append("")
    parts.append(f"- **来源**：`{source_path}`")
    parts.append(f"- **schema_version**：{_esc(doc.get('schema_version'))}")
    parts.append("")
    run = doc.get("run") or {}
    if isinstance(run, dict):
        parts.append("## 运行元数据")
        parts.append("")
        parts.append("| 字段 | 值 |")
        parts.append("|------|-----|")
        for k in (
            "run_id",
            "created_at",
            "run_kind_effective",
            "artifact_path",
            "artifact_fingerprint",
            "window_start",
            "window_end",
            "gitlab_group",
        ):
            if run.get(k) is not None:
                parts.append(f"| {k} | {_esc(run.get(k))} |")
        ing = run.get("ingest") or {}
        if isinstance(ing, dict) and ing.get("commit_row_count") is not None:
            parts.append(f"| ingest.commit_row_count | {_esc(ing.get('commit_row_count'))} |")
        sm = run.get("scores_merge") or {}
        if isinstance(sm, dict) and sm:
            parts.append(f"| scores_merge | {_esc(json.dumps(sm, ensure_ascii=False))} |")
        parts.append("")
    wf = doc.get("workflow") or {}
    if isinstance(wf, dict):
        parts.append("## workflow 摘要")
        parts.append("")
        parts.append("| 字段 | 值 |")
        parts.append("|------|-----|")
        for k in ("evidence_tier", "derived_next_run_recommendation", "reason_zh"):
            if wf.get(k) is not None:
                parts.append(f"| {k} | {_esc(wf.get(k))} |")
        parts.append("")
    people = doc.get("people") or []
    parts.append(f"## 必评人员（共 {len(people) if isinstance(people, list) else 0} 人）")
    parts.append("")
    if isinstance(people, list):
        for p in people:
            if isinstance(p, dict):
                parts.extend(_person_section(p))
    parts.append("---")
    parts.append("")
    parts.append("*权威数据以 JSON 为准；本文件为二次整理。*")
    parts.append("")
    return "\n".join(parts)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True, help="evaluation_run.v1 JSON (often *-scored.json)")
    p.add_argument("-o", "--output", type=Path, default=None, help="Output .md (default: <stem>.md next to input)")
    args = p.parse_args()
    inp = args.input.resolve()
    if not inp.is_file():
        print(f"not found: {inp}", file=sys.stderr)
        return 1
    doc: dict[str, Any] = json.loads(inp.read_text(encoding="utf-8"))
    out = args.output or (inp.parent / f"{inp.stem}.md")
    out = out.resolve()
    text = render_markdown(doc, source_path=str(inp))
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
