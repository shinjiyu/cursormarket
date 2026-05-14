"""Audit artifact vs ``evaluation_scope``; print JSON summary to stdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def audit_artifact(artifact: dict[str, Any], *, scope: dict[str, Any] | None) -> dict[str, Any]:
    rows = artifact.get("commit_events") or []
    if not isinstance(rows, list):
        rows = []
    stable = {
        str(e.get("person_key", ""))
        for e in rows
        if isinstance(e, dict) and not str(e.get("person_key", "")).startswith("unknown:")
    }

    scope_src = scope or (artifact.get("meta") or {}).get("evaluation_scope")
    if not isinstance(scope_src, dict):
        return {"error": "no_evaluation_scope", "stable_distinct": len(stable)}

    people = scope_src.get("required_people") or []
    if not isinstance(people, list):
        people = []

    coverage: list[dict[str, Any]] = []
    for entry in people:
        if not isinstance(entry, dict):
            continue
        keys = entry.get("person_keys") or []
        if not isinstance(keys, list):
            keys = []
        matched = [k for k in keys if k in stable]
        coverage.append(
            {
                "display_zh": entry.get("display_zh"),
                "game_zh": entry.get("game_zh"),
                "person_keys": keys,
                "matched_in_artifact": matched,
                "has_any_commit": bool(matched),
            }
        )

    missing = [c["display_zh"] for c in coverage if not c["has_any_commit"]]
    return {"stable_distinct": len(stable), "coverage": coverage, "missing_display_zh": missing}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True)
    p.add_argument("--scope-file", type=Path, default=None)
    args = p.parse_args()

    art = json.loads(args.input.read_text(encoding="utf-8"))
    scope = None
    if args.scope_file:
        scope = json.loads(args.scope_file.read_text(encoding="utf-8"))

    summary = audit_artifact(art, scope=scope)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
