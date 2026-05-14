"""Attach a **lightweight repo catalog** to artifact ``meta.repo_catalog`` for Agent-driven local review.

Writes HTTPS clone URLs derived from ``meta.gitlab_base_url`` + ``project_path`` (``.git`` suffix).
Does **not** clone repositories (no disk, no full-group checkout). Optional: fetch ``default_branch``
per ``project_id`` via GitLab API.

``recent_shas`` per row: bounded sample from ``commit_events`` (newest first) so Agent knows
where to start; full history remains in ``commit_events``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from org_contributor_pipeline.env_loader import load_repo_dotenv
from org_contributor_pipeline.ingest.gitlab_commits import build_gitlab_headers, resolve_gitlab_token


def _https_clone_url(gitlab_base_url: str, project_path: str) -> str:
    base = (gitlab_base_url or "").strip().rstrip("/")
    path = (project_path or "").strip().strip("/")
    return f"{base}/{path}.git"


def _ssh_clone_url(gitlab_base_url: str, project_path: str) -> str:
    host = urlparse(gitlab_base_url).netloc or ""
    path = (project_path or "").strip().strip("/")
    ns = path.replace("/", ":")
    return f"git@{host}:{ns}.git"


def _fetch_default_branch(client: httpx.Client, project_id: str) -> str | None:
    if not project_id:
        return None
    pid = quote(str(project_id), safe="")
    r = client.get(f"/projects/{pid}", params={"statistics": "false"})
    if r.status_code >= 400:
        return None
    data = r.json()
    if not isinstance(data, dict):
        return None
    b = data.get("default_branch")
    return str(b) if b else None


def build_repo_catalog(
    artifact: dict[str, Any],
    *,
    url_style: str,
    max_shas_per_project: int,
    fetch_default_branch: bool,
    gitlab_token: str,
    gitlab_api_base: str,
) -> dict[str, Any]:
    meta = artifact.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    base_url = str(meta.get("gitlab_base_url") or "").strip()
    if not base_url:
        raise ValueError("artifact.meta.gitlab_base_url is required to build clone URLs")

    rows = artifact.get("commit_events") or []
    if not isinstance(rows, list):
        raise ValueError("artifact.commit_events must be a list")

    by_path: dict[str, list[tuple[str, str]]] = defaultdict(list)
    id_by_path: dict[str, str] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        path = str(r.get("project_path", "")).strip()
        if not path:
            continue
        sha = str(r.get("sha", "")).strip()
        when = str(r.get("committed_at", "")).strip()
        if path not in id_by_path and r.get("project_id") is not None:
            id_by_path[path] = str(r.get("project_id"))
        if sha:
            by_path[path].append((when, sha))

    for path in by_path:
        by_path[path].sort(key=lambda t: t[0], reverse=True)

    client: httpx.Client | None = None
    if fetch_default_branch:
        if not gitlab_token:
            raise ValueError("--fetch-default-branch requires GITLAB_TOKEN or --token-file")
        api = gitlab_api_base.rstrip("/").rstrip("/") + "/api/v4"
        client = httpx.Client(base_url=api, headers=build_gitlab_headers(gitlab_token), timeout=60.0)

    catalog: list[dict[str, Any]] = []
    try:
        for path in sorted(by_path.keys()):
            pid = id_by_path.get(path, "")
            shas = [s for _, s in by_path[path][: max(0, max_shas_per_project)]]
            clone_https = _https_clone_url(base_url, path)
            clone_ssh = _ssh_clone_url(base_url, path) if url_style == "ssh" else None

            default_branch: str | None = None
            if client is not None and pid:
                default_branch = _fetch_default_branch(client, pid)

            entry: dict[str, Any] = {
                "project_id": pid,
                "project_path": path,
                "clone_url_https": clone_https,
                "default_branch": default_branch,
                "recent_shas": shas,
                "recent_shas_note_zh": f"至多 {max_shas_per_project} 条本仓最近提交（按 committed_at）；全量 sha 见 commit_events。",
            }
            if clone_ssh:
                entry["clone_url_ssh"] = clone_ssh
            catalog.append(entry)
    finally:
        if client is not None:
            client.close()

    meta = dict(meta)
    meta["repo_catalog"] = catalog
    meta["repo_catalog_meta"] = {
        "schema_version": 1,
        "url_style": url_style,
        "max_shas_per_project": max_shas_per_project,
        "fetch_default_branch": fetch_default_branch,
        "project_count": len(catalog),
        "usage_zh": "流水线不自动 clone。Agent 按需选择最少仓库与 shallow 深度，用 recent_shas 或 commit_events 检出再读代码；勿克隆整组所有仓。",
    }
    out = dict(artifact)
    out["meta"] = meta
    return out


def main() -> int:
    load_repo_dotenv()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument(
        "--gitlab-url",
        default=os.environ.get("GITLAB_URL", "https://gitlab.fingergame.com"),
        help="Used only when --fetch-default-branch (API host = this origin)",
    )
    p.add_argument("--token", default="", help="PAT for --fetch-default-branch")
    p.add_argument("--token-file", default="", help="First-line PAT file")
    p.add_argument(
        "--url-style",
        choices=("https", "ssh"),
        default="https",
        help="https: clone_url_https only; ssh: also clone_url_ssh (HTTPS row still filled as primary)",
    )
    p.add_argument("--max-shas-per-project", type=int, default=24, help="Cap recent_shas list size per repo")
    p.add_argument(
        "--fetch-default-branch",
        action="store_true",
        help="GET /projects/:id for each project_id (extra API calls)",
    )
    args = p.parse_args()

    token = ""
    if args.fetch_default_branch:
        try:
            token = resolve_gitlab_token(cli_token=args.token, token_file=args.token_file)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 2
        if not token:
            print("Missing token for --fetch-default-branch", file=sys.stderr)
            return 2

    art = json.loads(args.input.read_text(encoding="utf-8"))
    try:
        out = build_repo_catalog(
            art,
            url_style=args.url_style,
            max_shas_per_project=args.max_shas_per_project,
            fetch_default_branch=args.fetch_default_branch,
            gitlab_token=token,
            gitlab_api_base=args.gitlab_url,
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n = out["meta"]["repo_catalog_meta"]["project_count"]
    print(f"Wrote {args.output} repo_catalog projects={n}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
