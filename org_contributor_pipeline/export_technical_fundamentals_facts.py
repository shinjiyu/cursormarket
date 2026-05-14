"""Emit technical-fundamentals fact tables (Markdown or JSON) from an artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from org_contributor_pipeline.evaluation_facts import (
    load_json,
    technical_fundamentals_facts_by_person,
)


def emit_markdown_from_facts(bundle: dict[str, Any]) -> str:
    people = bundle.get("people") or []
    lines: list[str] = []
    lines.append("# 基础技术能力 — 事实层明细（从 artifact 抽取）\n")
    lines.append("本表为 **可机器汇总的指标**；**不等价** `dimensions.json` 里四个 L2 的完整技术评审。\n")
    lines.append("\n## 各 L2 与数据源的对应关系\n\n")
    lines.append("| L2（中文） | 本 artifact 中是否有专用量化 | 本报告中的数据 |\n")
    lines.append("|------------|------------------------------|----------------|\n")
    lines.append("| 数据结构、算法与复杂度 | 无 | `title_signal.fix_like_*` 命中数（弱）；大 diff 仅作体量线索 |\n")
    lines.append("| 语言深度与运行栈 | 无 | `path_taxonomy` 桶分布 + **commit_diff** 路径后缀 Top |\n")
    lines.append("| 数据与持久化 | 无 | 无自动指标；需 MR/迁移类材料 |\n")
    lines.append("| 设计表达与工程化底座 | 部分 | `title_signal.cicd_*` / `quality_gate_*` + extension/common 路径桶 |\n")
    lines.append("\n---\n")

    lines.append("\n## 1. 窗口内提交总量（每人）\n\n")
    lines.append("| 显示名 | person_key | evidence_gate | 提交条数 | +行 | −行 | 活跃项目数 | 首交日 | 末交日 |\n")
    lines.append("|--------|------------|---------------|----------|------|------|------------|--------|--------|\n")
    for p in people:
        w = p.get("window_activity") or {}
        lines.append(
            f"| {p.get('display_zh','')} | `{p.get('person_key','')}` | {p.get('evidence_gate','')} | "
            f"{w.get('commit_rows')} | {w.get('insertions')} | {w.get('deletions')} | "
            f"{w.get('distinct_projects')} | {w.get('first_day')} | {w.get('last_day')} |\n"
        )

    lines.append("\n## 2. commit_diff（GitLab enrich）覆盖\n\n")
    lines.append("| 显示名 | status=ok 条数 | truncated 条数 | diff 路径后缀 Top |\n")
    lines.append("|--------|----------------|----------------|-------------------|\n")
    for p in people:
        st = p.get("commit_diff") or {}
        top = st.get("diff_path_suffix_top") or []
        top_s = ", ".join(f"{x.get('suffix')}({x.get('count')})" for x in top) or "—"
        lines.append(
            f"| {p.get('display_zh','')} | {st.get('commit_diff_ok')} | "
            f"{st.get('commit_diff_truncated_commits')} | {top_s} |\n"
        )

    lines.append("\n## 3. 标题关键词信号（按人汇总；低置信）\n\n")
    lines.append(
        "| 显示名 | cicd | observability | quality_gate | fix_like | game_biz | merge_like |\n"
        "|--------|------|-----------------|--------------|----------|----------|------------|\n"
    )
    for p in people:
        s = p.get("title_signal_commit_hits") or {}
        lines.append(
            f"| {p.get('display_zh','')} | {s.get('cicd')} | {s.get('observability')} | {s.get('quality_gate')} | "
            f"{s.get('fix_like')} | {s.get('game_biz')} | {s.get('merge_like')} |\n"
        )

    lines.append("\n## 4. path_taxonomy（路径粗分）\n\n")
    for p in people:
        lines.append(f"### {p.get('display_zh')} (`{p.get('person_key')}`)\n\n")
        buckets = p.get("path_taxonomy_buckets") or {}
        if not buckets:
            lines.append("（无）\n\n")
            continue
        lines.append("| bucket | commits |\n|--------|--------|\n")
        for b, n in buckets.items():
            lines.append(f"| `{b}` | {n} |\n")
        lines.append("\n")

    lines.append("\n## 5. 体量最大的提交样例（每人最多 5 条）\n\n")
    for p in people:
        lines.append(f"### {p.get('display_zh')}\n\n")
        for c in p.get("largest_commits_sample") or []:
            lines.append(
                f"- `{c.get('sha','')[:12]}` … **{c.get('lines_changed')}** 行 — `{c.get('project_path','')}` — {c.get('title','')}\n"
            )
        lines.append("\n")

    return "".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True, help="Artifact JSON")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output path (.md or .json)")
    p.add_argument(
        "--format",
        choices=("md", "json", "auto"),
        default="auto",
        help="auto: infer from -o suffix",
    )
    args = p.parse_args()
    art = load_json(args.input)
    bundle = technical_fundamentals_facts_by_person(art)

    fmt = args.format
    if fmt == "auto":
        fmt = "json" if args.output.suffix.lower() == ".json" else "md"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        payload = {"schema_version": "technical_fundamentals_facts.v1", **bundle}
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        args.output.write_text(emit_markdown_from_facts(bundle), encoding="utf-8")
    print(f"Wrote {args.output} ({fmt})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
