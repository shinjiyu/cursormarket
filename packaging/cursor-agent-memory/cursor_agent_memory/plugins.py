from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .storage import AppStore, utc_now_iso


class PluginEngine:
    def __init__(self, store: AppStore) -> None:
        self.store = store
        self.handlers = {
            "plugin-sensitive-scan": self._sensitive_scan,
            "plugin-metadata-enricher": self._metadata_enricher,
            "plugin-audit-download": self._audit_download,
        }

    def run(self, hook_name: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for plugin in self.store.list_plugins():
            if plugin["hook_name"] != hook_name or not plugin["enabled"]:
                continue
            handler = self.handlers.get(plugin["id"])
            if handler is None:
                continue
            result = handler(context, plugin)
            results.append(result)
            self._record_plugin_run(plugin, context, result)
        return results

    def _record_plugin_run(
        self,
        plugin: dict[str, Any],
        context: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        bundle_id = context.get("bundle_id")
        version_id = context.get("version_id")
        with self.store.connect() as connection:
            connection.execute(
                """
                INSERT INTO plugin_runs (id, plugin_id, hook_name, bundle_id, version_id, status, summary, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.store.make_id("prun"),
                    plugin["id"],
                    plugin["hook_name"],
                    bundle_id,
                    version_id,
                    result.get("status", "ok"),
                    result.get("message"),
                    json.dumps(result, ensure_ascii=False),
                    utc_now_iso(),
                ),
            )

    def _sensitive_scan(self, context: dict[str, Any], plugin: dict[str, Any]) -> dict[str, Any]:
        config = json.loads(plugin["config_json"])
        terms = config.get("terms", [])
        file_path = context.get("file_path")
        if not file_path:
            return {"status": "ok", "message": "No file to scan."}
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            return {"status": "warn", "message": "Could not scan uploaded file."}

        hits = [term for term in terms if term.lower() in content]
        if not hits:
            return {"status": "ok", "message": "No obvious sensitive terms detected."}
        return {
            "status": "warn",
            "message": f"Sensitive terms detected: {', '.join(hits)}",
            "hits": hits,
        }

    def _metadata_enricher(self, context: dict[str, Any], plugin: dict[str, Any]) -> dict[str, Any]:
        metadata = context.get("metadata", {})
        tags = list(metadata.get("tags") or [])
        if metadata.get("problem_type") and metadata["problem_type"] not in tags:
            tags.append(metadata["problem_type"])
        metadata["tags"] = sorted({tag for tag in tags if tag})
        return {
            "status": "ok",
            "message": "Metadata normalized.",
            "metadata": metadata,
        }

    def _audit_download(self, context: dict[str, Any], plugin: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "message": "Download audited.",
            "bundle_id": context.get("bundle_id"),
            "version_id": context.get("version_id"),
        }

