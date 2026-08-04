from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def json_loads(payload: str | None, fallback: Any) -> Any:
    if not payload:
        return fallback
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return fallback


@dataclass
class AppPaths:
    root: Path
    db_path: Path
    storage_dir: Path


def build_app_paths() -> AppPaths:
    root = Path(os.environ.get("CURSOR_AGENT_MEMORY_DATA_DIR", "app_data"))
    return AppPaths(
        root=root,
        db_path=root / "app.sqlite3",
        storage_dir=root / "bundles",
    )


class AppStore:
    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = paths or build_app_paths()
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self.paths.storage_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_plugins()
        self._seed_demo_data()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.paths.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    email TEXT,
                    department TEXT,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(provider, external_id)
                );

                CREATE TABLE IF NOT EXISTS bundles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    project TEXT,
                    repo TEXT,
                    problem_type TEXT,
                    tags_csv TEXT,
                    sensitivity TEXT NOT NULL,
                    short_note TEXT,
                    uploader_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latest_version_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bundle_versions (
                    id TEXT PRIMARY KEY,
                    bundle_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    checksum_sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    manifest_json TEXT NOT NULL,
                    preview_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS access_policies (
                    id TEXT PRIMARY KEY,
                    bundle_id TEXT NOT NULL UNIQUE,
                    visibility TEXT NOT NULL,
                    allowed_roles_csv TEXT,
                    allowed_teams_csv TEXT,
                    require_approval INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS plugin_definitions (
                    id TEXT PRIMARY KEY,
                    hook_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS plugin_runs (
                    id TEXT PRIMARY KEY,
                    plugin_id TEXT NOT NULL,
                    hook_name TEXT NOT NULL,
                    bundle_id TEXT,
                    version_id TEXT,
                    status TEXT NOT NULL,
                    summary TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS usage_events (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT,
                    event_name TEXT NOT NULL,
                    bundle_id TEXT,
                    version_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS download_grants (
                    id TEXT PRIMARY KEY,
                    token TEXT NOT NULL UNIQUE,
                    actor_id TEXT NOT NULL,
                    bundle_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    decision_reason TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _seed_plugins(self) -> None:
        defaults = [
            {
                "id": "plugin-sensitive-scan",
                "hook_name": "before_upload",
                "name": "Sensitive Scan",
                "provider": "builtin",
                "config_json": json_dumps({"terms": ["password", "secret", "token", "api_key"]}),
            },
            {
                "id": "plugin-metadata-enricher",
                "hook_name": "before_upload",
                "name": "Metadata Enricher",
                "provider": "builtin",
                "config_json": json_dumps({}),
            },
            {
                "id": "plugin-audit-download",
                "hook_name": "after_download",
                "name": "Download Audit",
                "provider": "builtin",
                "config_json": json_dumps({}),
            },
        ]
        now = utc_now_iso()
        with self.connect() as connection:
            existing = {
                row["id"] for row in connection.execute("SELECT id FROM plugin_definitions").fetchall()
            }
            for plugin in defaults:
                if plugin["id"] in existing:
                    continue
                connection.execute(
                    """
                    INSERT INTO plugin_definitions (id, hook_name, name, provider, enabled, config_json, created_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        plugin["id"],
                        plugin["hook_name"],
                        plugin["name"],
                        plugin["provider"],
                        plugin["config_json"],
                        now,
                    ),
                )

    def _seed_demo_data(self) -> None:
        with self.connect() as connection:
            count = connection.execute("SELECT COUNT(*) AS count FROM bundles").fetchone()["count"]
        if count:
            return

        export_dir = Path("out") / "cursor-export-full" / "normalized" / "sessions"
        if not export_dir.exists():
            return

        demo_user = self.upsert_user(
            provider="demo",
            external_id="seed-admin",
            display_name="Seed Admin",
            email="seed@example.com",
            department="Platform",
            role="admin",
        )
        files = sorted(export_dir.glob("*.json"))[:6]
        for file_path in files:
            with file_path.open("rb") as handle:
                metadata = self.build_metadata_from_json(file_path)
                self.create_bundle_with_version(
                    uploader_id=demo_user["id"],
                    metadata=metadata,
                    file_name=file_path.name,
                    file_handle=handle,
                    visibility="internal",
                )

    def upsert_user(
        self,
        provider: str,
        external_id: str,
        display_name: str,
        email: str | None,
        department: str | None,
        role: str,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        user_id = f"{provider}:{external_id}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO users (id, provider, external_id, display_name, email, department, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, external_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    email = excluded.email,
                    department = excluded.department,
                    role = excluded.role
                """,
                (user_id, provider, external_id, display_name, email, department, role, now),
            )
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def list_catalog(
        self,
        query: str = "",
        project: str = "",
        problem_type: str = "",
        sensitivity: str = "",
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT b.*, bv.manifest_json, bv.preview_json, u.display_name AS uploader_name
            FROM bundles b
            LEFT JOIN bundle_versions bv ON bv.id = b.latest_version_id
            LEFT JOIN users u ON u.id = b.uploader_id
            WHERE 1 = 1
        """
        params: list[Any] = []
        if query:
            like_query = f"%{query.lower()}%"
            sql += " AND (LOWER(b.title) LIKE ? OR LOWER(COALESCE(b.project, '')) LIKE ? OR LOWER(COALESCE(b.tags_csv, '')) LIKE ? OR LOWER(COALESCE(b.short_note, '')) LIKE ?)"
            params.extend([like_query, like_query, like_query, like_query])
        if project:
            sql += " AND b.project = ?"
            params.append(project)
        if problem_type:
            sql += " AND b.problem_type = ?"
            params.append(problem_type)
        if sensitivity:
            sql += " AND b.sensitivity = ?"
            params.append(sensitivity)
        sql += " ORDER BY b.updated_at DESC"

        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["manifest"] = json_loads(item.pop("manifest_json"), {})
            item["preview"] = json_loads(item.pop("preview_json"), {})
            item["tags"] = [part for part in (item.get("tags_csv") or "").split(",") if part]
            results.append(item)
        return results

    def list_filter_values(self) -> dict[str, list[str]]:
        with self.connect() as connection:
            projects = [
                row["project"]
                for row in connection.execute(
                    "SELECT DISTINCT project FROM bundles WHERE project IS NOT NULL AND project != '' ORDER BY project"
                ).fetchall()
            ]
            problem_types = [
                row["problem_type"]
                for row in connection.execute(
                    "SELECT DISTINCT problem_type FROM bundles WHERE problem_type IS NOT NULL AND problem_type != '' ORDER BY problem_type"
                ).fetchall()
            ]
            sensitivities = [
                row["sensitivity"]
                for row in connection.execute(
                    "SELECT DISTINCT sensitivity FROM bundles ORDER BY sensitivity"
                ).fetchall()
            ]
        return {
            "projects": projects,
            "problem_types": problem_types,
            "sensitivities": sensitivities,
        }

    def get_bundle(self, bundle_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            bundle_row = connection.execute(
                """
                SELECT b.*, u.display_name AS uploader_name
                FROM bundles b
                LEFT JOIN users u ON u.id = b.uploader_id
                WHERE b.id = ?
                """,
                (bundle_id,),
            ).fetchone()
            if bundle_row is None:
                return None

            versions = connection.execute(
                "SELECT * FROM bundle_versions WHERE bundle_id = ? ORDER BY created_at DESC",
                (bundle_id,),
            ).fetchall()
            policy = connection.execute(
                "SELECT * FROM access_policies WHERE bundle_id = ?",
                (bundle_id,),
            ).fetchone()
            plugin_runs = connection.execute(
                "SELECT * FROM plugin_runs WHERE bundle_id = ? ORDER BY created_at DESC LIMIT 20",
                (bundle_id,),
            ).fetchall()

        bundle = dict(bundle_row)
        bundle["tags"] = [part for part in (bundle.get("tags_csv") or "").split(",") if part]
        bundle["versions"] = []
        for version in versions:
            version_item = dict(version)
            version_item["manifest"] = json_loads(version_item.pop("manifest_json"), {})
            version_item["preview"] = json_loads(version_item.pop("preview_json"), {})
            bundle["versions"].append(version_item)
        bundle["policy"] = dict(policy) if policy else None
        bundle["plugin_runs"] = [dict(item) for item in plugin_runs]
        return bundle

    def list_downloads_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT ue.*, b.title, bv.filename
                FROM usage_events ue
                LEFT JOIN bundles b ON b.id = ue.bundle_id
                LEFT JOIN bundle_versions bv ON bv.id = ue.version_id
                WHERE ue.actor_id = ? AND ue.event_name = 'downloaded'
                ORDER BY ue.created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_plugins(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM plugin_definitions ORDER BY hook_name, name"
            ).fetchall()
        return [dict(row) for row in rows]

    def toggle_plugin(self, plugin_id: str) -> None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT enabled FROM plugin_definitions WHERE id = ?",
                (plugin_id,),
            ).fetchone()
            if row is None:
                return
            next_value = 0 if row["enabled"] else 1
            connection.execute(
                "UPDATE plugin_definitions SET enabled = ? WHERE id = ?",
                (next_value, plugin_id),
            )

    def list_recent_audit(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT ue.*, u.display_name AS actor_name, b.title
                FROM usage_events ue
                LEFT JOIN users u ON u.id = ue.actor_id
                LEFT JOIN bundles b ON b.id = ue.bundle_id
                ORDER BY ue.created_at DESC
                LIMIT 50
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def record_usage_event(
        self,
        event_name: str,
        actor_id: str | None,
        bundle_id: str | None = None,
        version_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO usage_events (id, actor_id, event_name, bundle_id, version_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.make_id("evt"),
                    actor_id,
                    event_name,
                    bundle_id,
                    version_id,
                    json_dumps(payload or {}),
                    utc_now_iso(),
                ),
            )

    def create_download_grant(
        self,
        actor_id: str,
        bundle_id: str,
        version_id: str,
        decision_reason: str,
        ttl_minutes: int = 10,
    ) -> str:
        token = secrets.token_urlsafe(24)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO download_grants (id, token, actor_id, bundle_id, version_id, expires_at, decision_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.make_id("grant"),
                    token,
                    actor_id,
                    bundle_id,
                    version_id,
                    (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).replace(microsecond=0).isoformat(),
                    decision_reason,
                    utc_now_iso(),
                ),
            )
        return token

    def resolve_download_grant(self, token: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT dg.*, bv.storage_path, bv.filename
                FROM download_grants dg
                JOIN bundle_versions bv ON bv.id = dg.version_id
                WHERE dg.token = ?
                """,
                (token,),
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            return None
        return payload

    def create_bundle_with_version(
        self,
        uploader_id: str,
        metadata: dict[str, Any],
        file_name: str,
        file_handle: BinaryIO,
        visibility: str,
    ) -> dict[str, Any]:
        bundle_id = self.make_id("bundle")
        version_id = self.make_id("ver")
        now = utc_now_iso()

        file_bytes = file_handle.read()
        checksum = hashlib.sha256(file_bytes).hexdigest()
        version_dir = self.paths.storage_dir / version_id
        version_dir.mkdir(parents=True, exist_ok=True)
        storage_path = version_dir / file_name
        with storage_path.open("wb") as output_handle:
            output_handle.write(file_bytes)

        manifest = metadata["manifest"]
        preview = metadata["preview"]

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO bundles (
                    id, title, project, repo, problem_type, tags_csv, sensitivity,
                    short_note, uploader_id, status, latest_version_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bundle_id,
                    metadata["title"],
                    metadata.get("project"),
                    metadata.get("repo"),
                    metadata.get("problem_type"),
                    ",".join(metadata.get("tags", [])),
                    metadata["sensitivity"],
                    metadata.get("short_note"),
                    uploader_id,
                    "published",
                    version_id,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO bundle_versions (
                    id, bundle_id, filename, storage_path, checksum_sha256, size_bytes,
                    manifest_json, preview_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    bundle_id,
                    file_name,
                    str(storage_path),
                    checksum,
                    len(file_bytes),
                    json_dumps(manifest),
                    json_dumps(preview),
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO access_policies (
                    id, bundle_id, visibility, allowed_roles_csv, allowed_teams_csv, require_approval, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    self.make_id("policy"),
                    bundle_id,
                    visibility,
                    "viewer,publisher,moderator,admin",
                    "",
                    now,
                    now,
                ),
            )

        self.record_usage_event(
            event_name="published",
            actor_id=uploader_id,
            bundle_id=bundle_id,
            version_id=version_id,
            payload={"title": metadata["title"]},
        )
        return self.get_bundle(bundle_id) or {}

    def create_bundle_from_existing_file(
        self,
        uploader_id: str,
        metadata: dict[str, Any],
        file_path: Path,
        visibility: str = "internal",
    ) -> dict[str, Any]:
        with file_path.open("rb") as handle:
            return self.create_bundle_with_version(
                uploader_id=uploader_id,
                metadata=metadata,
                file_name=file_path.name,
                file_handle=handle,
                visibility=visibility,
            )

    def build_metadata_from_json(self, file_path: Path) -> dict[str, Any]:
        with file_path.open("r", encoding="utf-8", errors="replace") as handle:
            payload = json.load(handle)
        title = payload.get("title") or payload.get("session_id") or file_path.stem
        manifest = {
            "message_count": payload.get("message_count", 0),
            "tool_count": len(payload.get("tool_events") or []),
            "transcript_event_count": payload.get("transcript_event_count", 0),
            "workspace_count": len(payload.get("workspaces") or []),
            "touched_file_count": len(payload.get("touched_files") or []),
            "tools_used": payload.get("tools_used") or [],
        }
        preview_messages = []
        for message in payload.get("messages") or []:
            summary = message.get("summary") or message.get("text")
            if summary:
                preview_messages.append(summary)
            if len(preview_messages) >= 3:
                break
        preview = {
            "first_user_message": payload.get("first_user_message"),
            "snippets": preview_messages,
        }
        workspaces = payload.get("workspaces") or []
        project = None
        if workspaces:
            project = workspaces[0].get("local_path") or workspaces[0].get("workspace_uri")
        return {
            "title": title,
            "project": project,
            "repo": project,
            "problem_type": "analysis",
            "tags": payload.get("tools_used", [])[:4],
            "sensitivity": "internal",
            "short_note": payload.get("first_user_message") or "Imported from Cursor session export.",
            "manifest": manifest,
            "preview": preview,
        }

    @staticmethod
    def make_id(prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(8)}"

