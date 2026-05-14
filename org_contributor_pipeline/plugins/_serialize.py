from __future__ import annotations

from dataclasses import asdict

from org_contributor_pipeline.models.schemas import PluginResult, PluginStatus


def plugin_result_to_row(pr: PluginResult) -> dict:
    d = asdict(pr)
    d["status"] = pr.status.value if isinstance(pr.status, PluginStatus) else str(pr.status)
    return d
