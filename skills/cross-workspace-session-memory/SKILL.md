---
name: cross-workspace-session-memory
description: Find and read past Cursor sessions across workspaces using the local Agent Memory MCP tools.
---

# Cross-workspace session memory

## When to use

- User refers to work done in **another Cursor window / workspace**.
- User wants to recover a past agent session (bug fix, design choice, command sequence).
- Current chat has no context, but local history likely does.

## Prerequisites

Tools come from the `cursor-agent-memory-logs` MCP server. They read a local export tree (default `~/.cursor-agent-memory/export`).

If tools return `manifest_not_found` / `session_index_not_found`:

1. Ask the user (or run, if shell is allowed) a one-shot sync:
   ```bash
   uvx --from "git+https://github.com/shinjiyu/cursormarket.git#subdirectory=packaging/cursor-agent-memory" cursor-agent-memory-sync --once
   ```
2. Retry the MCP tools.

Keep the export fresh with hourly sync (`cursor-agent-memory-sync --once` on a schedule) or a long-lived daemon.

## Workflow

1. `cursor_logs_read_manifest` — confirm export exists and is recent.
2. `cursor_logs_search_sessions` or `cursor_logs_list_sessions` — narrow candidates by title / workspace path / keywords.
3. `cursor_logs_get_session` — load one session (payloads may be truncated; summarize, do not dump raw JSON to the user).
4. Answer with concrete findings (what was tried, decisions, file paths) and cite session title + workspace when useful.

## Rules

- Prefer MCP tools over manually browsing `~/.cursor/projects/*/agent-transcripts`.
- Do not upload export JSON to git, gist, or remote services — it contains conversation text and code snippets.
- If the user only needs the current workspace transcript, use the open chat / project transcripts first; use this skill for **cross-workspace** recall.
