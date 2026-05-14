"""Ingest commits from a GitLab group (and subgroups) into pipeline artifact JSON.

On startup, loads repository-root ``.env`` into the process environment (see
``org_contributor_pipeline.env_loader``) so you can set ``GITLAB_TOKEN``,
``GITLAB_URL``, ``GITLAB_TOKEN_FILE``, etc. without exporting in the shell.

Auth resolution (first non-empty wins):

1. ``--token`` (discouraged: shell history).
2. ``--token-file`` or env ``GITLAB_TOKEN_FILE``: path to a UTF-8 file whose **first line** is the token.
3. Env ``GITLAB_TOKEN`` (often populated from ``.env``).

Token needs ``read_api`` (and typically ``read_repository`` for commit listing).

Optional: set ``GITLAB_AUTH=bearer`` in ``.env`` if your token must be sent as
``Authorization: Bearer …`` (some OAuth / instance tokens); default is
``PRIVATE-TOKEN`` header.

API: GitLab REST v4. Docs: https://docs.gitlab.com/ee/api/rest/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterator
from pathlib import Path
from urllib.parse import quote

import httpx

from org_contributor_pipeline.env_loader import load_repo_dotenv
from org_contributor_pipeline.models.schemas import CommitEvent

DEFAULT_PER_PAGE = 100


def resolve_gitlab_token(*, cli_token: str, token_file: str) -> str:
    """Resolve PAT without logging the value."""
    t = (cli_token or "").strip()
    if t:
        return t
    path = (token_file or os.environ.get("GITLAB_TOKEN_FILE", "")).strip()
    if path:
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"GITLAB_TOKEN / --token-file: not a file: {p}")
        raw = p.read_text(encoding="utf-8")
        line = (raw.splitlines()[0] if raw.strip() else "").strip()
        if line:
            return line
    return (os.environ.get("GITLAB_TOKEN", "") or "").strip()


def _iso_z(dt: str | None) -> str:
    if not dt:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if dt.endswith("Z"):
        return dt
    return dt


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _encode_group_path(group_path: str) -> str:
    return quote(group_path.strip(), safe="")


def _paginate(
    client: httpx.Client,
    path: str,
    params: dict[str, Any],
    *,
    max_pages: int,
) -> Iterator[list[Any]]:
    base = dict(params)
    for page in range(1, max_pages + 1):
        base["page"] = page
        base.setdefault("per_page", DEFAULT_PER_PAGE)
        r = client.get(path, params=base)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "60"))
            time.sleep(min(wait, 120))
            r = client.get(path, params=base)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise TypeError(f"Expected JSON list from {path}, got {type(data).__name__}")
        if not data:
            break
        yield data
        if len(data) < base["per_page"]:
            break


def list_group_projects(
    client: httpx.Client,
    group_path: str,
    *,
    include_subgroups: bool,
    archived: bool,
    max_pages: int,
) -> list[dict[str, Any]]:
    gid = _encode_group_path(group_path)
    out: list[dict[str, Any]] = []
    params: dict[str, Any] = {
        "include_subgroups": "true" if include_subgroups else "false",
        "archived": "true" if archived else "false",
        "per_page": DEFAULT_PER_PAGE,
    }
    for batch in _paginate(client, f"/groups/{gid}/projects", params, max_pages=max_pages):
        out.extend(batch)
    return out


def list_project_commits(
    client: httpx.Client,
    project_id: str | int,
    *,
    since: str,
    until: str,
    all_branches: bool,
    with_stats: bool,
    max_pages: int,
) -> list[dict[str, Any]]:
    pid = quote(str(project_id), safe="")
    params: dict[str, Any] = {
        "since": since,
        "until": until,
        "with_stats": "true" if with_stats else "false",
        "per_page": DEFAULT_PER_PAGE,
    }
    if all_branches:
        params["all"] = "true"
    out: list[dict[str, Any]] = []
    for batch in _paginate(
        client,
        f"/projects/{pid}/repository/commits",
        params,
        max_pages=max_pages,
    ):
        out.extend(batch)
    return out


def _project_filter(path: str, include: re.Pattern[str] | None, exclude: re.Pattern[str] | None) -> bool:
    if include is not None and not include.search(path):
        return False
    if exclude is not None and exclude.search(path):
        return False
    return True


def commit_to_event(project: dict[str, Any], row: dict[str, Any]) -> CommitEvent:
    stats = row.get("stats") or {}
    additions = int(stats.get("additions") or 0)
    deletions = int(stats.get("deletions") or 0)
    email = _norm_email(row.get("author_email") or "")
    name = (row.get("author_name") or "").strip() or "unknown"
    sha = row.get("id") or row.get("short_id") or ""
    authored = row.get("authored_date") or row.get("committed_date") or row.get("created_at")
    return CommitEvent(
        project_id=str(project.get("id", "")),
        project_path=str(project.get("path_with_namespace", "")),
        sha=str(sha),
        committed_at=_iso_z(authored),
        author_email=email or "unknown@unknown.local",
        author_name=name,
        person_key=email or f"unknown:{sha[:8]}",
        insertions=additions,
        deletions=deletions,
        files_changed=0,
        metadata={
            "title": (row.get("title") or "")[:500],
            "web_url": row.get("web_url"),
            "stats_total_lines": stats.get("total"),
            "files_changed_note": "GitLab list API does not provide file count; use 0 or enrich offline.",
        },
    )


def build_artifact(
    *,
    commit_events: list[CommitEvent],
    window_start: str,
    window_end: str,
    gitlab_group: str,
    gitlab_base: str,
    included_project_paths: list[str],
    extra_meta: dict[str, Any],
) -> dict[str, Any]:
    paths = sorted(set(included_project_paths))
    meta: dict[str, Any] = {
        "window_start": window_start,
        "window_end": window_end,
        "timezone": "UTC",
        "gitlab_group": gitlab_group,
        "gitlab_base_url": gitlab_base.rstrip("/"),
        "included_project_paths": paths,
        "submodule_policy": "Vendor/submodule paths are not auto-discounted in this ingest; apply mailmap and path rules downstream.",
        "mailmap_version": "none (person_key = normalized author_email)",
        "ingest": {
            "source": "gitlab_api_v4",
            "commit_row_count": len(commit_events),
        },
        **extra_meta,
    }
    return {
        "artifact_version": 1,
        "meta": meta,
        "commit_events": [asdict(e) for e in commit_events],
        "plugin_results": [],
    }


def build_gitlab_headers(token: str) -> dict[str, str]:
    """``GITLAB_AUTH=private_token`` (default) or ``bearer`` for OAuth-style access tokens."""
    mode = (os.environ.get("GITLAB_AUTH", "private_token") or "private_token").strip().lower()
    if mode in ("bearer", "oauth", "oauth2"):
        return {"Authorization": f"Bearer {token}"}
    return {"PRIVATE-TOKEN": token}


def ingest_group(
    *,
    base_url: str,
    token: str,
    group_path: str,
    since: str,
    until: str,
    include_subgroups: bool,
    archived: bool,
    all_branches: bool,
    with_stats: bool,
    max_project_pages: int,
    max_commit_pages_per_project: int,
    project_include: str | None,
    project_exclude: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    api = base_url.rstrip("/") + "/api/v4"
    headers = build_gitlab_headers(token)
    include_re = re.compile(project_include) if project_include else None
    exclude_re = re.compile(project_exclude) if project_exclude else None

    with httpx.Client(base_url=api, headers=headers, timeout=120.0) as client:
        projects = list_group_projects(
            client,
            group_path,
            include_subgroups=include_subgroups,
            archived=archived,
            max_pages=max_project_pages,
        )
        projects = sorted(projects, key=lambda p: str(p.get("path_with_namespace", "")))
        filtered = [
            p
            for p in projects
            if _project_filter(str(p.get("path_with_namespace", "")), include_re, exclude_re)
        ]

        if dry_run:
            return build_artifact(
                commit_events=[],
                window_start=since,
                window_end=until,
                gitlab_group=group_path,
                gitlab_base=base_url,
                included_project_paths=[str(p.get("path_with_namespace", "")) for p in filtered],
                extra_meta={
                    "dry_run": True,
                    "projects_seen": len(projects),
                    "projects_after_filter": len(filtered),
                },
            )

        events: list[CommitEvent] = []
        for proj in filtered:
            pid = proj.get("id")
            path = str(proj.get("path_with_namespace", ""))
            if pid is None or not path:
                continue
            try:
                commits = list_project_commits(
                    client,
                    pid,
                    since=since,
                    until=until,
                    all_branches=all_branches,
                    with_stats=with_stats,
                    max_pages=max_commit_pages_per_project,
                )
            except httpx.HTTPStatusError as e:
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
            for c in commits:
                events.append(commit_to_event(proj, c))

        events.sort(key=lambda e: (e.committed_at, e.project_path, e.sha))
        return build_artifact(
            commit_events=events,
            window_start=since,
            window_end=until,
            gitlab_group=group_path,
            gitlab_base=base_url,
            included_project_paths=[str(p.get("path_with_namespace", "")) for p in filtered],
            extra_meta={
                "projects_scanned": len(filtered),
                "projects_listed_total": len(projects),
            },
        )


def main() -> int:
    load_repo_dotenv()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--gitlab-url",
        default=os.environ.get("GITLAB_URL", "https://gitlab.fingergame.com"),
        help="GitLab origin (no /api/v4); override with GITLAB_URL in .env",
    )
    p.add_argument("--group", required=True, help="Group path_with_namespace segment, e.g. h5_game_sh_tpe or parent/sub")
    p.add_argument("--since", required=True, help="ISO8601 start (inclusive), e.g. 2026-01-01T00:00:00Z")
    p.add_argument(
        "--until",
        required=True,
        help='Commits strictly before this instant (GitLab "until" query is exclusive); use day-after window at 00:00:00Z',
    )
    p.add_argument("-o", "--output", type=str, required=True, help="Output JSON path")
    p.add_argument("--token", default="", help="PAT (prefer --token-file to avoid shell history)")
    p.add_argument(
        "--token-file",
        default="",
        help="Read PAT from first line of this file (or set GITLAB_TOKEN_FILE).",
    )
    p.add_argument("--no-subgroups", action="store_true", help="Only direct projects under the group")
    p.add_argument("--archived", action="store_true", help="Include archived projects")
    p.add_argument("--all-branches", action="store_true", help="Pass all=true to commits API (heavier)")
    p.add_argument("--no-stats", action="store_true", help="Omit with_stats (faster; insertions/deletions become 0)")
    p.add_argument("--max-project-pages", type=int, default=100, help="Safety cap when listing group projects")
    p.add_argument(
        "--max-commit-pages-per-project",
        type=int,
        default=500,
        help="Safety cap per project (pages * per_page commits)",
    )
    p.add_argument("--include-project-regex", default="", help="Only paths matching this regex")
    p.add_argument("--exclude-project-regex", default="", help="Exclude paths matching this regex")
    p.add_argument("--dry-run", action="store_true", help="List filtered projects only; no commits fetched")
    args = p.parse_args()

    try:
        token = resolve_gitlab_token(cli_token=args.token, token_file=args.token_file)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    if not token:
        print(
            "Missing token: use --token-file, GITLAB_TOKEN_FILE, GITLAB_TOKEN, or --token",
            file=sys.stderr,
        )
        return 2
    if len(token) < 8:
        print(
            "Warning: token is very short; if ingest returns 401, check .env / scopes.",
            file=sys.stderr,
        )

    try:
        payload = ingest_group(
            base_url=args.gitlab_url,
            token=token,
            group_path=args.group,
            since=args.since,
            until=args.until,
            include_subgroups=not args.no_subgroups,
            archived=args.archived,
            all_branches=args.all_branches,
            with_stats=not args.no_stats,
            max_project_pages=args.max_project_pages,
            max_commit_pages_per_project=args.max_commit_pages_per_project,
            project_include=args.include_project_regex or None,
            project_exclude=args.exclude_project_regex or None,
            dry_run=args.dry_run,
        )
    except httpx.HTTPStatusError as e:
        url = str(e.request.url) if e.request else ""
        snippet = (e.response.text or "")[:800] if e.response is not None else ""
        print(f"GitLab HTTP {e.response.status_code if e.response else '?'} {url}\n{snippet}", file=sys.stderr)
        return 1

    out_path = os.path.abspath(args.output)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    n = len(payload.get("commit_events") or [])
    print(f"Wrote {out_path} commits={n} projects_in_meta={len(payload['meta'].get('included_project_paths', []))}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
