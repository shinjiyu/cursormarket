"""一键自检：compileall → demo enrich + merge 必评名单 + scope_audit →（若存在）全量 scoped 必评覆盖严格校验。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from org_contributor_pipeline.merge_evaluation_scope import default_review_framework_path, default_scope_path, merge_scope
from org_contributor_pipeline.scope_audit import audit_artifact


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_compileall() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "compileall", "org_contributor_pipeline", "-q"],
        cwd=_repo_root(),
    )
    if r.returncode != 0:
        raise SystemExit(f"compileall failed exit={r.returncode}")


def _run_module(mod: str, *args: str) -> None:
    r = subprocess.run([sys.executable, "-m", mod, *args], cwd=_repo_root())
    if r.returncode != 0:
        raise SystemExit(f"{' '.join((mod,) + args)} failed exit={r.returncode}")


def _quick_demo_chain() -> tuple[dict[str, Any], set[str]]:
    root = _repo_root()
    demo = root / "org_contributor_pipeline" / "artifacts" / "generated" / "demo_pipeline_input.json"
    if not demo.is_file():
        raise SystemExit(f"missing demo artifact: {demo}")
    scope = json.loads(default_scope_path().read_text(encoding="utf-8"))
    rf_path = default_review_framework_path()
    rf = json.loads(rf_path.read_text(encoding="utf-8")) if rf_path.is_file() else None
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        enr = tdir / "enriched.json"
        scp = tdir / "scoped.json"
        _run_module(
            "org_contributor_pipeline.enrich_artifact",
            "-i",
            str(demo),
            "-o",
            str(enr),
            "--plugin",
            "all",
            "--replace",
        )
        art = json.loads(enr.read_text(encoding="utf-8"))
        plugin_ids = {r.get("plugin_id") for r in (art.get("plugin_results") or []) if isinstance(r, dict)}
        out = merge_scope(art, scope=scope, review_framework=rf)
        scp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        art2 = json.loads(scp.read_text(encoding="utf-8"))
        summary = audit_artifact(art2, scope=None)
        return summary, plugin_ids


def _strict_artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"artifact not found: {path}")
    art = json.loads(path.read_text(encoding="utf-8"))
    return audit_artifact(art, scope=None)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--skip-quick",
        action="store_true",
        help="Skip compileall + demo enrich/merge/audit",
    )
    p.add_argument(
        "--strict-artifact",
        type=Path,
        default=None,
        metavar="PATH",
        help="Require evaluation_scope coverage (missing_display_zh empty)",
    )
    p.add_argument(
        "--no-default-strict",
        action="store_true",
        help="Do not auto-run strict on gitlab_group_artifact_scoped.json when present",
    )
    args = p.parse_args()

    root = _repo_root()
    snapshot_scoped = (
        root / "org_contributor_pipeline" / "snapshots" / "last_org_eval_20260513" / "gitlab_group_artifact_scoped.json"
    )
    default_scoped = (
        snapshot_scoped
        if snapshot_scoped.is_file()
        else (root / "org_contributor_pipeline" / "artifacts" / "generated" / "gitlab_group_artifact_scoped.json")
    )

    if not args.skip_quick:
        print("== compileall org_contributor_pipeline ==", flush=True)
        _run_compileall()
        print("== quick: demo enrich + merge + scope_audit ==", flush=True)
        summary, plugin_ids = _quick_demo_chain()
        miss = summary.get("missing_display_zh") or []
        if len(miss) != 8:
            print("QUICK_FAIL: expected 8 missing required people on demo, got:", miss, flush=True)
            return 1
        need = {"delivery_traceability", "commit_title_signals", "path_taxonomy_proxy", "identity_footprint"}
        if not need <= plugin_ids:
            print("QUICK_FAIL: plugin_ids missing", need - plugin_ids, flush=True)
            return 1
        print("QUICK_OK: demo flags 8 missing; four plugin families present", flush=True)

    strict_path = args.strict_artifact
    if strict_path is None and not args.no_default_strict and default_scoped.is_file():
        strict_path = default_scoped

    if strict_path is not None:
        print(f"== strict: scope coverage {strict_path} ==", flush=True)
        s2 = _strict_artifact(strict_path)
        miss2 = s2.get("missing_display_zh") or []
        if miss2:
            print("STRICT_FAIL: required people without commits in artifact:", miss2, flush=True)
            return 1
        print("STRICT_OK: all required_people have commit_events in window", flush=True)

    print("VERIFY_ALL_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
