"""Merge ``evaluation_run_scores_patch.v1`` into a base ``evaluation_run.v1`` JSON."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell_key(c: dict[str, Any]) -> tuple[str, str]:
    return (str(c.get("l1_id") or ""), str(c.get("l2_id") or ""))


def merge_patch(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if patch.get("schema_version") != "evaluation_run_scores_patch.v1":
        raise ValueError("patch.schema_version must be evaluation_run_scores_patch.v1")
    out = json.loads(json.dumps(base))
    people_out = out.get("people")
    if not isinstance(people_out, list):
        raise ValueError("base.people must be a list")

    by_pk: dict[str, dict[str, Any]] = {}
    for p in people_out:
        if isinstance(p, dict) and p.get("person_key"):
            by_pk[str(p["person_key"])] = p

    for pp in patch.get("people") or []:
        if not isinstance(pp, dict):
            continue
        pk = str(pp.get("person_key") or "")
        if pk not in by_pk:
            raise ValueError(f"patch references unknown person_key: {pk}")
        target = by_pk[pk]
        old_scores = target.get("mandatory_l2_scores") or []
        patch_scores = pp.get("mandatory_l2_scores") or []
        if not isinstance(old_scores, list) or not isinstance(patch_scores, list):
            raise ValueError("mandatory_l2_scores must be lists")
        if len(patch_scores) != len(old_scores):
            raise ValueError(
                f"person {pk}: patch mandatory_l2_scores length {len(patch_scores)} "
                f"!= base length {len(old_scores)}"
            )
        patch_by_key = {_cell_key(c): c for c in patch_scores if isinstance(c, dict)}
        merged: list[dict[str, Any]] = []
        for cell in old_scores:
            if not isinstance(cell, dict):
                merged.append(cell)
                continue
            key = _cell_key(cell)
            pcell = patch_by_key.get(key)
            if not pcell:
                raise ValueError(f"person {pk}: missing patch cell for {key}")
            if _cell_key(pcell) != key:
                raise ValueError(f"person {pk}: patch cell order/key mismatch for {key}")
            new_cell = dict(cell)
            for k in ("grade", "confidence", "narrative_zh", "filled_by", "filled_at", "inherited_from_run_id"):
                if k in pcell and pcell[k] is not None:
                    new_cell[k] = pcell[k]
            merged.append(new_cell)
        target["mandatory_l2_scores"] = merged

    run = out.setdefault("run", {})
    if isinstance(run, dict):
        run["scores_merge"] = {
            "schema_version": patch.get("schema_version"),
            "patch_filled_by": patch.get("filled_by"),
        }
    return out


def extract_json_object(text: str) -> dict[str, Any]:
    """Find first complete top-level JSON object (handles optional markdown fences)."""
    s = text.strip()
    try:
        o = json.loads(s)
        if isinstance(o, dict):
            return o
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.IGNORECASE)
    if fence:
        inner = fence.group(1).strip()
        try:
            o = json.loads(inner)
            if isinstance(o, dict):
                return o
        except json.JSONDecodeError:
            pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _end = dec.raw_decode(s[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("No valid JSON object found in text")


def build_stub_scores_patch(
    base: dict[str, Any],
    *,
    filled_by: str = "pipeline_stub",
    narrative_zh: str = "（流水线占位）未走研判层；请用 cursor agent 或人工打分后替换。",
) -> dict[str, Any]:
    """Build a valid ``evaluation_run_scores_patch.v1`` that fills every L2 cell (for CI / wiring checks)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    people_out: list[dict[str, Any]] = []
    for p in base.get("people") or []:
        if not isinstance(p, dict):
            continue
        pk = p.get("person_key")
        if not pk:
            continue
        scores: list[dict[str, Any]] = []
        for cell in p.get("mandatory_l2_scores") or []:
            if not isinstance(cell, dict):
                continue
            scores.append(
                {
                    "l1_id": cell.get("l1_id"),
                    "l2_id": cell.get("l2_id"),
                    "grade": "待评",
                    "confidence": "低",
                    "narrative_zh": narrative_zh,
                    "filled_by": filled_by,
                    "filled_at": now,
                }
            )
        people_out.append({"person_key": str(pk), "mandatory_l2_scores": scores})
    return {
        "schema_version": "evaluation_run_scores_patch.v1",
        "filled_by": filled_by,
        "people": people_out,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-b", "--base", type=Path, required=True, help="Base evaluation_run.v1 JSON")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output merged JSON")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("-p", "--patch", type=Path, help="Patch JSON (evaluation_run_scores_patch.v1)")
    g.add_argument("--from-log", type=Path, dest="from_log", help="Agent stdout log; extract JSON patch")
    g.add_argument(
        "--stub-from-base",
        action="store_true",
        help="Synthesize a placeholder patch from base (no LLM); marks scores_merge.patch_filled_by=pipeline_stub",
    )
    args = p.parse_args()

    base = load_json(args.base)
    if args.stub_from_base:
        patch = build_stub_scores_patch(base)
    elif args.patch:
        patch = load_json(args.patch)
    else:
        assert args.from_log is not None
        patch = extract_json_object(args.from_log.read_text(encoding="utf-8"))

    merged = merge_patch(base, patch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
