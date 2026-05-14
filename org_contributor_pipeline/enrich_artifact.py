"""Merge plugin outputs into an existing pipeline artifact JSON (stdin-free CLI)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from org_contributor_pipeline.plugins.commit_title_signals import (
    PLUGIN_ID as TITLE_PLUGIN_ID,
    PLUGIN_VERSION as TITLE_PLUGIN_VERSION,
    run_commit_title_signals_on_events,
)
from org_contributor_pipeline.plugins.delivery_traceability import (
    PLUGIN_ID as DELIVERY_PLUGIN_ID,
    PLUGIN_VERSION as DELIVERY_PLUGIN_VERSION,
    run_delivery_traceability_on_events,
)
from org_contributor_pipeline.plugins.identity_footprint import (
    PLUGIN_ID as IDENTITY_PLUGIN_ID,
    PLUGIN_VERSION as IDENTITY_PLUGIN_VERSION,
    run_identity_footprint_on_events,
)
from org_contributor_pipeline.plugins.path_taxonomy import (
    PLUGIN_ID as PATH_PLUGIN_ID,
    PLUGIN_VERSION as PATH_PLUGIN_VERSION,
    run_path_taxonomy_on_events,
)

PluginRunner = Callable[..., list[dict[str, Any]]]

PLUGIN_SPECS_IN_ORDER: list[tuple[str, str, PluginRunner]] = [
    (DELIVERY_PLUGIN_ID, DELIVERY_PLUGIN_VERSION, run_delivery_traceability_on_events),
    (TITLE_PLUGIN_ID, TITLE_PLUGIN_VERSION, run_commit_title_signals_on_events),
    (PATH_PLUGIN_ID, PATH_PLUGIN_VERSION, run_path_taxonomy_on_events),
    (IDENTITY_PLUGIN_ID, IDENTITY_PLUGIN_VERSION, run_identity_footprint_on_events),
]

KNOWN_PLUGIN_IDS: frozenset[str] = frozenset(pid for pid, _, _ in PLUGIN_SPECS_IN_ORDER)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _window_and_rows(artifact: dict[str, Any]) -> tuple[dict[str, Any], str, str, list[dict[str, Any]]]:
    meta = artifact.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    ws = str(meta.get("window_start", ""))
    we = str(meta.get("window_end", ""))
    rows = artifact.get("commit_events") or []
    if not isinstance(rows, list):
        rows = []
    return meta, ws, we, [r for r in rows if isinstance(r, dict)]


def _filter_plugin_rows(existing: list[dict[str, Any]], remove_ids: frozenset[str]) -> list[dict[str, Any]]:
    return [r for r in existing if isinstance(r, dict) and r.get("plugin_id") not in remove_ids]


def enrich_artifact(
    artifact: dict[str, Any],
    *,
    plugin: str,
    replace: bool,
) -> dict[str, Any]:
    meta, ws, we, rows = _window_and_rows(artifact)
    existing = artifact.get("plugin_results") or []
    if not isinstance(existing, list):
        existing = []
    existing_rows = [r for r in existing if isinstance(r, dict)]

    if plugin == "all":
        remove_ids = KNOWN_PLUGIN_IDS if replace else frozenset()
    else:
        remove_ids = frozenset({plugin}) if replace else frozenset()

    merged = _filter_plugin_rows(existing_rows, remove_ids)

    new_rows: list[dict[str, Any]] = []
    applied_tags: list[str] = []

    specs = PLUGIN_SPECS_IN_ORDER if plugin == "all" else [(pid, ver, fn) for pid, ver, fn in PLUGIN_SPECS_IN_ORDER if pid == plugin]

    if not specs:
        raise ValueError(f"unknown plugin: {plugin}")

    for pid, ver, runner in specs:
        new_rows.extend(runner(commit_events=rows, window_start=ws, window_end=we))
        tag = f"{pid}@{ver}"
        if tag not in applied_tags:
            applied_tags.append(tag)

    merged = merged + new_rows

    plugins_meta = list(meta.get("plugins_applied") or [])
    if not isinstance(plugins_meta, list):
        plugins_meta = []
    for tag in applied_tags:
        if tag not in plugins_meta:
            plugins_meta.append(tag)
    meta["plugins_applied"] = plugins_meta

    out = dict(artifact)
    out["meta"] = meta
    out["plugin_results"] = merged
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True, help="Input artifact JSON")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output artifact JSON")
    p.add_argument(
        "--plugin",
        choices=["all", *[pid for pid, _, _ in PLUGIN_SPECS_IN_ORDER]],
        default="delivery_traceability",
        help="Which plugin to run, or all registered commit_events plugins",
    )
    p.add_argument(
        "--replace",
        action="store_true",
        help="Remove prior rows for the selected plugin(s) before appending (for all: every built-in plugin_id)",
    )
    args = p.parse_args()

    art = _load_json(args.input)
    out = enrich_artifact(art, plugin=args.plugin, replace=args.replace)
    _write_json(args.output, out)
    n = len(out.get("plugin_results") or [])
    print(f"Wrote {args.output} plugin_result_rows={n}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
