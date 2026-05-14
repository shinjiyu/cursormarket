"""Merge rubric JSON into artifact ``meta`` (``evaluation_scope``, ``review_framework``)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _package_rubric_dir() -> Path:
    return Path(__file__).resolve().parent / "rubric"


def default_scope_path() -> Path:
    return _package_rubric_dir() / "evaluation_scope.json"


def default_review_framework_path() -> Path:
    return _package_rubric_dir() / "review_framework.json"


def merge_scope(
    artifact: dict[str, Any],
    *,
    scope: dict[str, Any],
    review_framework: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = artifact.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    meta = dict(meta)
    meta["evaluation_scope"] = scope
    if review_framework is not None:
        meta["review_framework"] = review_framework
    out = dict(artifact)
    out["meta"] = meta
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--scope-file", type=Path, default=None, help="Override default rubric/evaluation_scope.json")
    p.add_argument(
        "--review-framework-file",
        type=Path,
        default=None,
        help="Override default rubric/review_framework.json (pass a nonexistent path to skip)",
    )
    p.add_argument(
        "--no-review-framework",
        action="store_true",
        help="Do not embed review_framework.json into meta",
    )
    args = p.parse_args()

    scope_path = args.scope_file or default_scope_path()
    art = json.loads(args.input.read_text(encoding="utf-8"))
    scope = json.loads(scope_path.read_text(encoding="utf-8"))

    rf: dict[str, Any] | None = None
    if not args.no_review_framework:
        rf_path = args.review_framework_file or default_review_framework_path()
        if rf_path.is_file():
            rf = json.loads(rf_path.read_text(encoding="utf-8"))
        else:
            print(f"warn: review_framework not found, skipped: {rf_path}", flush=True)

    out = merge_scope(art, scope=scope, review_framework=rf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len((scope.get("required_people") or []) if isinstance(scope, dict) else [])
    extra = " +review_framework" if rf is not None else ""
    print(f"Wrote {args.output} evaluation_scope entries={n}{extra}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
