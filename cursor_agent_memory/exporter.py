from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def decode_blob(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)

    stripped = text.strip()
    if not stripped:
        return ""

    if stripped[0] in "{[" or stripped in {"true", "false", "null"} or stripped[0].isdigit():
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return text
    return text


def dump_json(path: Path, payload: Any, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if pretty:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
        else:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "unknown"


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, (list, dict)):
            if value:
                return value
            continue
        return value
    return None


def flatten_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, list):
        parts = [flatten_text(item) for item in value]
        merged = "\n".join(part for part in parts if part)
        return merged or None
    if isinstance(value, dict):
        for key in ("text", "content", "value", "message", "body"):
            if key in value:
                text = flatten_text(value[key])
                if text:
                    return text
        parts = [flatten_text(item) for item in value.values()]
        merged = "\n".join(part for part in parts if part)
        return merged or None
    return str(value)


def summarize_payload(payload: Any, limit: int = 240) -> str | None:
    text = flatten_text(payload)
    if not text:
        return None
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def map_role(raw_role: Any) -> str:
    if raw_role in (1, "user"):
        return "user"
    if raw_role in (2, "assistant"):
        return "assistant"
    if isinstance(raw_role, str):
        lowered = raw_role.lower()
        if lowered in {"tool", "system", "assistant", "user"}:
            return lowered
    return "unknown"


def uri_to_path(uri: str | None) -> str | None:
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        path = unquote(parsed.path or "")
        if re.match(r"^/[A-Za-z]:", path):
            return path[1:]
        return path or None
    return None


def normalize_workspace_identifier(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    uri = value.get("uri") or {}
    return {
        "workspace_id": value.get("id"),
        "uri": uri.get("external") or uri.get("path"),
        "local_path": uri.get("fsPath") or uri_to_path(uri.get("external") or uri.get("path")),
    }


def guess_tool_name(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("toolName", "name", "tool", "callName", "displayName"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def guess_status(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("status", "result", "state", "outcome"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def guess_path(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("path", "filePath", "target_file", "file", "uri"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                for nested_key in ("fsPath", "path", "external"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, str) and nested_value.strip():
                        return nested_value.strip()
    return None


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def collect_strings(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        text = value.strip()
        if 8 <= len(text) <= 160 and "\n" not in text and "\r" not in text:
            found.add(text)
        return found
    if isinstance(value, list):
        for item in value:
            found.update(collect_strings(item))
        return found
    if isinstance(value, dict):
        for item in value.values():
            found.update(collect_strings(item))
    return found


class SqliteSnapshot:
    def __init__(self, source: Path):
        self.source = source
        self.tempdir: tempfile.TemporaryDirectory[str] | None = None
        self.snapshot_path: Path | None = None
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> sqlite3.Connection:
        self.tempdir = tempfile.TemporaryDirectory(prefix="cursor_agent_memory_")
        snapshot_dir = Path(self.tempdir.name)
        snapshot_path = snapshot_dir / self.source.name
        shutil.copy2(self.source, snapshot_path)
        for suffix in ("-wal", "-shm"):
            sibling = Path(str(self.source) + suffix)
            if sibling.exists():
                shutil.copy2(sibling, snapshot_dir / sibling.name)
        self.snapshot_path = snapshot_path
        self.connection = sqlite3.connect(str(snapshot_path))
        self.connection.row_factory = sqlite3.Row
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.tempdir is not None:
            self.tempdir.cleanup()


def default_cursor_user_root() -> Path:
    """Best-effort default location of Cursor's per-user state directory.

    Windows: %APPDATA%\\Cursor\\User
    macOS:   ~/Library/Application Support/Cursor/User
    Linux:   ~/.config/Cursor/User
    """
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Cursor" / "User"
        return Path.home() / "AppData" / "Roaming" / "Cursor" / "User"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User"
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    config_root = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return config_root / "Cursor" / "User"


class CursorMemoryExporter:
    def __init__(
        self,
        output_dir: Path,
        cursor_user_root: Path | None = None,
        projects_root: Path | None = None,
        limit: int | None = None,
        include_raw: bool = False,
        pretty: bool = True,
    ) -> None:
        if cursor_user_root is None:
            cursor_user_root = default_cursor_user_root()

        if projects_root is None:
            projects_root = Path.home() / ".cursor" / "projects"

        self.output_dir = output_dir
        self.cursor_user_root = cursor_user_root
        self.projects_root = projects_root
        self.limit = limit
        self.include_raw = include_raw
        self.pretty = pretty

    def export(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        workspaces = self._discover_workspaces()
        transcripts_by_session, transcript_files = self._discover_transcripts()
        sessions, raw_sessions, headers = self._extract_sessions(workspaces, transcripts_by_session)
        selected_session_ids = {session["session_id"] for session in sessions}
        selected_transcript_file_count = sum(
            len(transcripts_by_session.get(session_id, []))
            for session_id in selected_session_ids
        )

        dump_json(self.output_dir / "manifest.json", {
            "schema_version": 1,
            "generated_at": utc_now_iso(),
            "cursor_user_root": str(self.cursor_user_root),
            "projects_root": str(self.projects_root),
            "session_count": len(sessions),
            "workspace_count": len(workspaces),
            "transcript_file_count": selected_transcript_file_count,
            "discovered_transcript_file_count": transcript_files,
        }, self.pretty)
        dump_json(self.output_dir / "normalized" / "workspaces.json", workspaces, self.pretty)
        dump_json(self.output_dir / "normalized" / "session_index.json", [
            {
                "session_id": session["session_id"],
                "title": session.get("title"),
                "workspace_paths": [item.get("local_path") for item in session.get("workspaces", []) if item.get("local_path")],
                "updated_at": session.get("updated_at"),
                "message_count": session.get("message_count"),
                "tools_used": session.get("tools_used", []),
                "source_kinds": session.get("source_kinds", []),
            }
            for session in sessions
        ], self.pretty)
        dump_json(self.output_dir / "raw" / "composer_headers.json", headers, self.pretty)

        for session in sessions:
            dump_json(
                self.output_dir / "normalized" / "sessions" / f"{safe_name(session['session_id'])}.json",
                session,
                self.pretty,
            )
        if self.include_raw:
            for session_id, payload in raw_sessions.items():
                dump_json(
                    self.output_dir / "raw" / "composer_data" / f"{safe_name(session_id)}.json",
                    payload,
                    self.pretty,
                )
            for session_id, transcript_records in transcripts_by_session.items():
                if session_id not in selected_session_ids:
                    continue
                for record in transcript_records:
                    target_name = f"{safe_name(session_id)}__{safe_name(record['file_name'])}.json"
                    dump_json(self.output_dir / "raw" / "transcripts" / target_name, record, self.pretty)

        return {
            "session_count": len(sessions),
            "workspace_count": len(workspaces),
            "transcript_file_count": selected_transcript_file_count,
            "discovered_transcript_file_count": transcript_files,
            "output_dir": str(self.output_dir),
        }

    def _discover_workspaces(self) -> list[dict[str, Any]]:
        root = self.cursor_user_root / "workspaceStorage"
        if not root.exists():
            return []

        workspaces: list[dict[str, Any]] = []
        for entry in sorted(root.iterdir(), key=lambda item: item.name):
            if not entry.is_dir():
                continue

            workspace_json = entry / "workspace.json"
            workspace_db = entry / "state.vscdb"
            workspace_payload = self._read_json_file(workspace_json)
            uri = None
            if isinstance(workspace_payload, dict):
                uri = workspace_payload.get("folder") or workspace_payload.get("workspace")

            session_refs: set[str] = set()
            if workspace_db.exists():
                session_refs = self._extract_workspace_session_refs(workspace_db)

            workspaces.append({
                "workspace_id": entry.name,
                "workspace_dir": str(entry),
                "workspace_json_path": str(workspace_json) if workspace_json.exists() else None,
                "workspace_db_path": str(workspace_db) if workspace_db.exists() else None,
                "workspace_uri": uri,
                "local_path": uri_to_path(uri),
                "discovered_session_refs": sorted(session_refs),
            })
        return workspaces

    def _discover_transcripts(self) -> tuple[dict[str, list[dict[str, Any]]], int]:
        transcripts_by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if not self.projects_root.exists():
            return transcripts_by_session, 0

        count = 0
        for path in self.projects_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".jsonl", ".txt"}:
                continue
            if "agent-transcripts" not in str(path).replace("\\", "/"):
                continue

            session_id = path.stem
            record = self._parse_transcript_file(path, session_id)
            transcripts_by_session[session_id].append(record)
            count += 1
        return transcripts_by_session, count

    def _extract_sessions(
        self,
        workspaces: list[dict[str, Any]],
        transcripts_by_session: dict[str, list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
        global_db = self.cursor_user_root / "globalStorage" / "state.vscdb"
        if not global_db.exists():
            raise RuntimeError(f"Cursor global database not found: {global_db}")

        workspace_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for workspace in workspaces:
            for session_id in workspace.get("discovered_session_refs", []):
                workspace_index[session_id].append({
                    "workspace_id": workspace.get("workspace_id"),
                    "local_path": workspace.get("local_path"),
                    "workspace_uri": workspace.get("workspace_uri"),
                })

        sessions: list[dict[str, Any]] = []
        raw_sessions: dict[str, Any] = {}

        with SqliteSnapshot(global_db) as connection:
            headers_payload = self._select_one(connection, "ItemTable", "composer.composerHeaders") or {}
            header_entries = headers_payload.get("allComposers", []) if isinstance(headers_payload, dict) else []
            headers_by_id = {
                entry.get("composerId"): entry
                for entry in header_entries
                if isinstance(entry, dict) and entry.get("composerId")
            }

            composer_rows = self._select_like(connection, "cursorDiskKV", "composerData:%")
            composer_data_by_id = {
                key.split(":", 1)[1]: value
                for key, value in composer_rows
                if ":" in key
            }

            all_session_ids = set(composer_data_by_id.keys()) | set(transcripts_by_session.keys())
            sessions_with_sort: list[tuple[int, dict[str, Any]]] = []

            for session_id in sorted(all_session_ids):
                composer_data = composer_data_by_id.get(session_id)
                header_entry = headers_by_id.get(session_id)

                bubble_rows = self._select_like(connection, "cursorDiskKV", f"bubbleId:{session_id}:%")
                checkpoint_rows = self._select_like(connection, "cursorDiskKV", f"checkpointId:{session_id}:%")
                request_context_rows = self._select_like(connection, "cursorDiskKV", f"messageRequestContext:{session_id}:%")

                session = self._normalize_session(
                    session_id=session_id,
                    composer_data=composer_data,
                    header_entry=header_entry,
                    bubble_rows=bubble_rows,
                    checkpoint_rows=checkpoint_rows,
                    request_context_rows=request_context_rows,
                    workspace_links=workspace_index.get(session_id, []),
                    transcript_records=transcripts_by_session.get(session_id, []),
                )
                sessions_with_sort.append((session.get("updated_at_ms") or 0, session))

                if self.include_raw and composer_data is not None:
                    raw_sessions[session_id] = composer_data

            sessions_with_sort.sort(key=lambda item: item[0], reverse=True)
            if self.limit is not None:
                sessions_with_sort = sessions_with_sort[: self.limit]
            sessions = [session for _, session in sessions_with_sort]
            raw_sessions = {
                session["session_id"]: raw_sessions[session["session_id"]]
                for session in sessions
                if session["session_id"] in raw_sessions
            }
            return sessions, raw_sessions, header_entries

    def _normalize_session(
        self,
        session_id: str,
        composer_data: Any,
        header_entry: dict[str, Any] | None,
        bubble_rows: list[tuple[str, Any]],
        checkpoint_rows: list[tuple[str, Any]],
        request_context_rows: list[tuple[str, Any]],
        workspace_links: list[dict[str, Any]],
        transcript_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        composer_data = composer_data if isinstance(composer_data, dict) else {}
        bubble_map = {
            key.rsplit(":", 1)[-1]: value
            for key, value in bubble_rows
            if isinstance(value, dict)
        }
        conversation_headers = composer_data.get("fullConversationHeadersOnly") or []
        legacy_map = composer_data.get("conversationMap") or {}

        messages: list[dict[str, Any]] = []
        if conversation_headers:
            for index, header in enumerate(conversation_headers):
                if not isinstance(header, dict):
                    continue
                bubble_id = header.get("bubbleId") or f"message-{index + 1}"
                payload = bubble_map.get(bubble_id)
                if payload is None and isinstance(legacy_map, dict):
                    payload = legacy_map.get(bubble_id)
                messages.append(self._normalize_message(index, bubble_id, header, payload))
        elif isinstance(legacy_map, dict) and legacy_map:
            sortable = []
            for bubble_id, payload in legacy_map.items():
                created_at = payload.get("createdAt") if isinstance(payload, dict) else 0
                sortable.append((created_at or 0, bubble_id, payload))
            for index, (_, bubble_id, payload) in enumerate(sorted(sortable, key=lambda item: item[0])):
                messages.append(self._normalize_message(index, bubble_id, {}, payload))

        checkpoints = [
            {
                "checkpoint_key": key,
                "checkpoint_id": key.rsplit(":", 1)[-1],
                "payload": value,
                "summary": summarize_payload(value),
            }
            for key, value in checkpoint_rows
        ]
        request_contexts = [
            {
                "request_context_key": key,
                "message_id": key.rsplit(":", 1)[-1],
                "payload": value,
                "summary": summarize_payload(value),
            }
            for key, value in request_context_rows
        ]

        transcript_summary = []
        transcript_events = []
        for record in transcript_records:
            transcript_summary.append({
                "path": record["path"],
                "event_count": record["event_count"],
                "event_kinds": record["event_kinds"],
            })
            transcript_events.extend(record["events"])

        tool_events = self._extract_tool_events(messages, transcript_events)
        tools_used = sorted({event["tool_name"] for event in tool_events if event.get("tool_name")})
        touched_files = sorted({
            path
            for path in (
                guess_path(event.get("payload"))
                for event in tool_events
            )
            if path
        })

        header_workspace = normalize_workspace_identifier(header_entry.get("workspaceIdentifier")) if isinstance(header_entry, dict) else None
        workspaces = list(workspace_links)
        if header_workspace and all(item.get("workspace_id") != header_workspace.get("workspace_id") for item in workspaces):
            workspaces.append(header_workspace)

        title = (
            composer_data.get("name")
            or (header_entry or {}).get("name")
            or first_non_empty(*(record.get("title") for record in transcript_records))
            or session_id
        )
        created_at_ms = composer_data.get("createdAt") or (header_entry or {}).get("createdAt")
        updated_at_ms = (
            composer_data.get("lastUpdatedAt")
            or (header_entry or {}).get("lastUpdatedAt")
            or created_at_ms
            or 0
        )
        first_user_message = next((message["text"] for message in messages if message["role"] == "user" and message["text"]), None)

        return {
            "schema_version": 1,
            "session_id": session_id,
            "title": title,
            "mode": first_non_empty(composer_data.get("unifiedMode"), composer_data.get("forceMode"), (header_entry or {}).get("unifiedMode")),
            "model_name": ((composer_data.get("modelConfig") or {}).get("modelName") if isinstance(composer_data.get("modelConfig"), dict) else None),
            "created_at_ms": created_at_ms,
            "updated_at_ms": updated_at_ms,
            "created_at": self._format_ts(created_at_ms),
            "updated_at": self._format_ts(updated_at_ms),
            "source_kinds": sorted([
                kind
                for kind, present in {
                    "global_sqlite": bool(composer_data),
                    "agent_transcript": bool(transcript_records),
                    "workspace_link": bool(workspaces),
                }.items()
                if present
            ]),
            "workspaces": workspaces,
            "message_count": len(messages),
            "messages": messages,
            "tool_events": tool_events,
            "tools_used": tools_used,
            "touched_files": touched_files,
            "first_user_message": first_user_message,
            "checkpoints": checkpoints,
            "request_contexts": request_contexts,
            "context": composer_data.get("context"),
            "transcript_files": transcript_summary,
            "transcript_event_count": sum(record["event_count"] for record in transcript_records),
        }

    def _normalize_message(
        self,
        index: int,
        bubble_id: str,
        header: dict[str, Any],
        payload: Any,
    ) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        grouping = header.get("grouping") if isinstance(header.get("grouping"), dict) else {}
        text = first_non_empty(
            payload.get("text"),
            flatten_text(payload.get("richText")),
            flatten_text(payload.get("content")),
            flatten_text(payload.get("markdown")),
        )
        role = map_role(first_non_empty(payload.get("role"), payload.get("type"), header.get("role"), header.get("type")))
        return {
            "order": index,
            "bubble_id": bubble_id,
            "role": role,
            "type": first_non_empty(payload.get("type"), header.get("type")),
            "created_at_raw": payload.get("createdAt"),
            "created_at": self._format_ts(payload.get("createdAt")),
            "text": text,
            "checkpoint_id": payload.get("checkpointId"),
            "tool_results": ensure_list(payload.get("toolResults")),
            "thinking_blocks": ensure_list(payload.get("allThinkingBlocks")),
            "code_blocks": ensure_list(payload.get("codeBlocks")),
            "suggested_code_blocks": ensure_list(payload.get("suggestedCodeBlocks")),
            "relevant_files": ensure_list(payload.get("relevantFiles")),
            "grouping": grouping,
            "summary": summarize_payload(text or payload),
        }

    def _extract_tool_events(
        self,
        messages: list[dict[str, Any]],
        transcript_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for message in messages:
            for item in message.get("tool_results") or []:
                events.append({
                    "source": "sqlite",
                    "message_bubble_id": message.get("bubble_id"),
                    "tool_name": guess_tool_name(item),
                    "status": guess_status(item),
                    "path": guess_path(item),
                    "summary": summarize_payload(item),
                    "payload": item,
                })
            grouping = message.get("grouping") or {}
            if grouping.get("toolCallId") or grouping.get("capabilityType") == 15:
                tool_number = grouping.get("toolFormerTool")
                events.append({
                    "source": "sqlite_grouping",
                    "message_bubble_id": message.get("bubble_id"),
                    "tool_name": grouping.get("toolName") or (f"cursor_tool_{tool_number}" if tool_number is not None else None),
                    "status": "grouped",
                    "path": None,
                    "summary": summarize_payload(grouping),
                    "payload": grouping,
                })

        for event in transcript_events:
            kind = (event.get("kind") or "").lower()
            tool_name = event.get("tool_name")
            if "tool" not in kind and not tool_name:
                continue
            events.append({
                "source": "transcript",
                "message_bubble_id": None,
                "tool_name": tool_name,
                "status": event.get("status"),
                "path": guess_path(event.get("payload")),
                "summary": event.get("summary"),
                "payload": event.get("payload"),
            })
        return events

    def _extract_workspace_session_refs(self, db_path: Path) -> set[str]:
        refs: set[str] = set()
        if not db_path.exists():
            return refs

        with SqliteSnapshot(db_path) as connection:
            composer_data = self._select_one(connection, "ItemTable", "composer.composerData")
            if isinstance(composer_data, dict):
                all_composers = composer_data.get("allComposers") or []
                for item in all_composers:
                    if isinstance(item, dict) and item.get("composerId"):
                        refs.add(item["composerId"])
                for key in ("selectedComposerIds", "lastFocusedComposerIds"):
                    values = composer_data.get(key) or []
                    if isinstance(values, list):
                        refs.update(value for value in values if isinstance(value, str))

            view_rows = self._select_like(connection, "ItemTable", "workbench.panel.composerChatViewPane.%")
            for _, payload in view_rows:
                refs.update(collect_strings(payload))
        return refs

    def _parse_transcript_file(self, path: Path, session_id: str) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        title = path.parent.name if path.parent.name != path.stem else path.stem

        with path.open("r", encoding="utf-8", errors="replace") as handle:
            if path.suffix.lower() == ".jsonl":
                for line_number, line in enumerate(handle, start=1):
                    text = line.strip()
                    if not text:
                        continue
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        events.append({
                            "line_number": line_number,
                            "kind": "text",
                            "tool_name": None,
                            "status": None,
                            "summary": summarize_payload(text),
                            "payload": {"text": text},
                        })
                        continue

                    expanded = self._expand_transcript_events(payload, line_number)
                    if expanded:
                        events.extend(expanded)
                    else:
                        kind = first_non_empty(payload.get("type"), payload.get("role"), payload.get("event"), "json")
                        events.append({
                            "line_number": line_number,
                            "kind": str(kind),
                            "tool_name": guess_tool_name(payload),
                            "status": guess_status(payload),
                            "summary": summarize_payload(
                                first_non_empty(
                                    payload.get("text"),
                                    payload.get("content"),
                                    payload.get("message"),
                                    payload,
                                )
                            ),
                            "payload": payload,
                        })
            else:
                content = handle.read()
                events.append({
                    "line_number": 1,
                    "kind": "text",
                    "tool_name": None,
                    "status": None,
                    "summary": summarize_payload(content),
                    "payload": {"text": content},
                })

        event_kinds = Counter(event["kind"] for event in events)
        return {
            "session_id": session_id,
            "path": str(path),
            "file_name": path.name,
            "title": title,
            "event_count": len(events),
            "event_kinds": dict(event_kinds),
            "events": events,
        }

    def _expand_transcript_events(self, payload: dict[str, Any], line_number: int) -> list[dict[str, Any]]:
        role = payload.get("role")
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            return []

        events: list[dict[str, Any]] = []
        for block_index, block in enumerate(content):
            if not isinstance(block, dict):
                continue
            block_type = block.get("type") or role or "content"
            block_payload = block.get("input") if block_type == "tool_use" else block
            events.append({
                "line_number": line_number,
                "block_index": block_index,
                "kind": str(block_type),
                "tool_name": block.get("name") if block_type == "tool_use" else guess_tool_name(block_payload),
                "status": guess_status(block_payload),
                "summary": summarize_payload(first_non_empty(block.get("text"), block_payload, payload)),
                "payload": block,
            })
        return events

    def _read_json_file(self, path: Path) -> Any:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return json.load(handle)

    def _select_one(self, connection: sqlite3.Connection, table: str, key: str) -> Any:
        row = connection.execute(f"SELECT value FROM {table} WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return decode_blob(row["value"])

    def _select_like(self, connection: sqlite3.Connection, table: str, pattern: str) -> list[tuple[str, Any]]:
        rows = connection.execute(
            f"SELECT key, value FROM {table} WHERE key LIKE ? ORDER BY key",
            (pattern,),
        ).fetchall()
        return [(row["key"], decode_blob(row["value"])) for row in rows]

    def _format_ts(self, value: Any) -> str | None:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(microsecond=0).isoformat()
            except ValueError:
                return value
        if not isinstance(value, (int, float)) or value <= 0:
            return None
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()
