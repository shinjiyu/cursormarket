"""Fetch per-commit unified diffs from GitLab and attach truncated excerpts to ``commit_events[].metadata.commit_diff``.

Run **after** ``gitlab_commits`` ingest (same ``GITLAB_URL`` / token as ingest). Intended for **targeted**
enrichment: full-window × all commits would be thousands of API calls — use caps and
``--only-evaluation-scope-persons`` when ``meta.evaluation_scope`` is present.

Writes structured blobs only (paths + truncated diff text); does not run an LLM.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from org_contributor_pipeline.env_loader import load_repo_dotenv
from org_contributor_pipeline.ingest.gitlab_commits import build_gitlab_headers, resolve_gitlab_token


def _person_keys_from_evaluation_scope(meta: dict[str, Any]) -> set[str] | None:
    es = meta.get("evaluation_scope")
    if not isinstance(es, dict):
        return None
    people = es.get("required_people") or []
    if not isinstance(people, list):
        return None
    keys: set[str] = set()
    for p in people:
        if not isinstance(p, dict):
            continue
        for k in p.get("person_keys") or []:
            if isinstance(k, str) and k.strip():
                keys.add(k.strip())
    return keys or None


def _diff_is_probably_binary(diff: str) -> bool:
    if not diff or len(diff) < 200:
        return False
    sample = diff[:8000]
    non_print = sum(1 for c in sample if ord(c) < 9 and c not in "\n\r\t")
    return non_print / max(len(sample), 1) > 0.02


def _truncate(s: str, limit: int) -> tuple[str, bool]:
    if len(s) <= limit:
        return s, False
    return s[:limit], True


def fetch_commit_diff(
    client: httpx.Client,
    project_id: str | int,
    sha: str,
) -> tuple[list[dict[str, Any]], str | None]:
    """Return (list of file diff dicts from API, error_message_or_None)."""
    pid = quote(str(project_id), safe="")
    sh = quote(sha, safe="")
    path = f"/projects/{pid}/repository/commits/{sh}/diff"
    r = client.get(path)
    if r.status_code == 429:
        wait = int(r.headers.get("Retry-After", "60"))
        time.sleep(min(wait, 120))
        r = client.get(path)
    if r.status_code == 404:
        return [], "http_404"
    if r.status_code >= 400:
        return [], f"http_{r.status_code}"
    data = r.json()
    if not isinstance(data, list):
        return [], "invalid_json"
    return data, None


def build_commit_diff_metadata(
    api_files: list[dict[str, Any]],
    *,
    max_files: int,
    max_chars_per_file: int,
    max_chars_total: int,
) -> dict[str, Any]:
    files_out: list[dict[str, Any]] = []
    total = 0
    truncated_commit = False
    for item in api_files[:max_files]:
        path = str(item.get("new_path") or item.get("old_path") or "")
        raw = item.get("diff")
        if not isinstance(raw, str):
            continue
        if _diff_is_probably_binary(raw):
            files_out.append({"path": path or "(binary)", "diff_excerpt": "", "skipped": "likely_binary"})
            continue
        room = max_chars_total - total
        if room <= 0:
            truncated_commit = True
            break
        cap = min(max_chars_per_file, room)
        excerpt, t1 = _truncate(raw, cap)
        total += len(excerpt)
        files_out.append(
            {
                "path": path,
                "diff_excerpt": excerpt,
                "truncated_file": t1,
            }
        )
        if t1 or total >= max_chars_total:
            truncated_commit = True
    return {
        "schema_version": 1,
        "status": "ok",
        "files_changed_count": len(api_files),
        "files_included": len(files_out),
        "truncated": truncated_commit or len(api_files) > max_files,
        "files": files_out,
    }


def select_commit_indices(
    rows: list[dict[str, Any]],
    *,
    only_person_keys: set[str] | None,
    max_commits: int,
    max_per_person: int,
) -> list[int]:
    indexed: list[tuple[int, str, str]] = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            continue
        pk = str(r.get("person_key", ""))
        if pk.startswith("unknown:"):
            continue
        if only_person_keys is not None and pk not in only_person_keys:
            continue
        when = str(r.get("committed_at", ""))
        sha = str(r.get("sha", ""))
        if not sha:
            continue
        indexed.append((i, when, pk))
    indexed.sort(key=lambda t: (t[1], t[2]), reverse=True)

    if max_per_person <= 0:
        return [t[0] for t in indexed[:max_commits]]

    per: dict[str, int] = {}
    out: list[int] = []
    for i, _when, pk in indexed:
        if per.get(pk, 0) >= max_per_person:
            continue
        out.append(i)
        per[pk] = per.get(pk, 0) + 1
        if len(out) >= max_commits:
            break
    return out


def enrich_artifact_commit_diffs(
    artifact: dict[str, Any],
    *,
    gitlab_url: str,
    token: str,
    max_commits: int,
    max_per_person: int,
    max_files: int,
    max_chars_per_file: int,
    max_chars_total: int,
    only_evaluation_scope_persons: bool,
    skip_existing_ok: bool,
) -> dict[str, Any]:
    rows = artifact.get("commit_events") or []
    if not isinstance(rows, list):
        raise ValueError("artifact.commit_events must be a list")
    rows = [r for r in rows if isinstance(r, dict)]

    meta = artifact.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}

    scope_keys: set[str] | None = None
    if only_evaluation_scope_persons:
        scope_keys = _person_keys_from_evaluation_scope(meta)
        if not scope_keys:
            raise ValueError(
                "meta.evaluation_scope.required_people has no person_keys — run merge_evaluation_scope first, "
                "or omit --only-evaluation-scope-persons."
            )

    indices = select_commit_indices(
        rows,
        only_person_keys=scope_keys,
        max_commits=max_commits,
        max_per_person=max_per_person,
    )

    api = gitlab_url.rstrip("/") + "/api/v4"
    headers = build_gitlab_headers(token)
    processed = 0
    skipped_existing = 0
    errors: dict[str, int] = {}

    with httpx.Client(base_url=api, headers=headers, timeout=120.0) as client:
        for idx in indices:
            row = rows[idx]
            meta_row = row.get("metadata")
            if not isinstance(meta_row, dict):
                meta_row = {}
            existing = meta_row.get("commit_diff")
            if skip_existing_ok and isinstance(existing, dict) and existing.get("status") == "ok":
                skipped_existing += 1
                continue

            pid = row.get("project_id")
            sha = str(row.get("sha", ""))
            if pid is None or not sha:
                continue

            api_files, err = fetch_commit_diff(client, pid, sha)
            if err:
                meta_row = dict(meta_row)
                meta_row["commit_diff"] = {
                    "schema_version": 1,
                    "status": err,
                    "truncated": False,
                    "files": [],
                }
                row["metadata"] = meta_row
                errors[err] = errors.get(err, 0) + 1
                processed += 1
                continue

            blob = build_commit_diff_metadata(
                api_files,
                max_files=max_files,
                max_chars_per_file=max_chars_per_file,
                max_chars_total=max_chars_total,
            )
            meta_row = dict(meta_row)
            meta_row["commit_diff"] = blob
            row["metadata"] = meta_row
            processed += 1

    meta = dict(meta)
    prev = meta.get("commit_diff_enrich") if isinstance(meta.get("commit_diff_enrich"), dict) else {}
    meta["commit_diff_enrich"] = {
        **prev,
        "schema_version": 1,
        "candidates_in_selection": len(indices),
        "commits_fetched_or_attached": processed,
        "skipped_existing_ok": skipped_existing,
        "only_evaluation_scope_persons": bool(only_evaluation_scope_persons),
        "max_commits": max_commits,
        "max_per_person": max_per_person,
        "error_counts": errors,
    }

    out = dict(artifact)
    out["meta"] = meta
    out["commit_events"] = rows
    return out


def main() -> int:
    load_repo_dotenv()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", type=Path, required=True, help="Ingest artifact JSON")
    p.add_argument("-o", "--output", type=Path, required=True, help="Output JSON path")
    p.add_argument(
        "--gitlab-url",
        default=os.environ.get("GITLAB_URL", "https://gitlab.fingergame.com"),
        help="GitLab origin (no /api/v4)",
    )
    p.add_argument("--token", default="", help="PAT (prefer --token-file)")
    p.add_argument("--token-file", default="", help="First-line PAT file or GITLAB_TOKEN_FILE")
    p.add_argument(
        "--max-commits",
        type=int,
        default=400,
        help="Hard cap on diff API calls (after person filter and per-person cap)",
    )
    p.add_argument(
        "--max-per-person",
        type=int,
        default=30,
        help="Max commits to fetch per person_key (0 = ignore, use only max-commits global order)",
    )
    p.add_argument("--max-files-per-commit", type=int, default=12, help="First N files from diff API")
    p.add_argument("--max-chars-per-file", type=int, default=8000, help="Truncate each file diff excerpt")
    p.add_argument("--max-chars-total-per-commit", type=int, default=32000, help="Total diff chars per commit")
    p.add_argument(
        "--only-evaluation-scope-persons",
        action="store_true",
        help="Only commits whose person_key appears in meta.evaluation_scope.required_people",
    )
    p.add_argument(
        "--skip-existing-ok",
        action="store_true",
        help="Skip rows that already have metadata.commit_diff.status=ok",
    )
    args = p.parse_args()

    try:
        token = resolve_gitlab_token(cli_token=args.token, token_file=args.token_file)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2
    if not token:
        print("Missing token: GITLAB_TOKEN, --token-file, or --token", file=sys.stderr)
        return 2

    art = json.loads(args.input.read_text(encoding="utf-8"))
    try:
        out = enrich_artifact_commit_diffs(
            art,
            gitlab_url=args.gitlab_url,
            token=token,
            max_commits=args.max_commits,
            max_per_person=args.max_per_person,
            max_files=args.max_files_per_commit,
            max_chars_per_file=args.max_chars_per_file,
            max_chars_total=args.max_chars_total_per_commit,
            only_evaluation_scope_persons=args.only_evaluation_scope_persons,
            skip_existing_ok=args.skip_existing_ok,
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    m = out["meta"]["commit_diff_enrich"]
    print(
        f"Wrote {args.output} commits_diff_enrich fetched={m['commits_fetched_or_attached']} "
        f"candidates={m['candidates_in_selection']} skipped_existing={m['skipped_existing_ok']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
