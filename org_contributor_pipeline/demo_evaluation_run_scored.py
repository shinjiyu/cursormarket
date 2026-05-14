"""Emit ``evaluation_run.v1`` from a scoped artifact, then merge **stub** scores (no LLM, no CLI).

Default input: ``artifacts/generated/gitlab_group_artifact_scoped.json``.
Outputs sit next to that file unless ``-o`` / ``--scored`` are set.

For real scores use ``run_fill_evaluation_scores`` without ``--stub`` (``cursor agent``), then merge.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from org_contributor_pipeline.emit_evaluation_run import build_evaluation_run
from org_contributor_pipeline.evaluation_facts import load_json
from org_contributor_pipeline.merge_evaluation_scores import build_stub_scores_patch, merge_patch


def _default_scoped() -> Path:
    return Path(__file__).resolve().parent / "artifacts" / "generated" / "gitlab_group_artifact_scoped.json"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-i",
        "--artifact",
        type=Path,
        default=None,
        help="Scoped enriched artifact (with meta.evaluation_scope + review_framework)",
    )
    p.add_argument(
        "-o",
        "--output-evaluation-run",
        type=Path,
        default=None,
        help="Base evaluation_run JSON (default: <artifact_dir>/evaluation_run-demo-scoped.json)",
    )
    p.add_argument(
        "--scored",
        type=Path,
        default=None,
        help="Merged scored JSON (default: <stem>-scored.json next to base output)",
    )
    args = p.parse_args()

    artifact_path = (args.artifact or _default_scoped()).resolve()
    if not artifact_path.is_file():
        print(f"artifact not found: {artifact_path}", file=sys.stderr)
        return 1

    out_base = args.output_evaluation_run or (artifact_path.parent / "evaluation_run-demo-scoped.json")
    out_base = out_base.resolve()
    scored_path = args.scored or (out_base.parent / f"{out_base.stem}-scored.json")

    art: dict[str, Any] = load_json(artifact_path)
    payload = build_evaluation_run(
        art,
        artifact_path=artifact_path,
        run_kind="full",
        baseline_json=None,
        pipeline_capability_epoch=1,
        embed_baseline="none",
    )
    out_base.parent.mkdir(parents=True, exist_ok=True)
    out_base.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_base}", flush=True)

    patch = build_stub_scores_patch(payload)
    merged = merge_patch(payload, patch)
    scored_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {scored_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
