# Cursor Agent Memory

Extract local Cursor sessions on Windows into agent-friendly JSON.

## What it does

This tool reads local Cursor data from:

- `%APPDATA%\Cursor\User\globalStorage\state.vscdb`
- `%APPDATA%\Cursor\User\workspaceStorage\*`
- `%USERPROFILE%\.cursor\projects\*\agent-transcripts\*`

It writes:

- `manifest.json` with extraction summary
- `normalized/workspaces.json` with workspace mapping
- `normalized/session_index.json` with a lightweight session list
- `normalized/sessions/*.json` with canonical session payloads
- optional `raw/*` artifacts when `--include-raw` is set

## Quick start

```powershell
python -m cursor_agent_memory --output .\out\cursor-export --include-raw
```

Or install it as a local CLI:

```powershell
pip install -e .
cursor-agent-memory --output .\out\cursor-export
```

## Useful flags

- `--limit 50` only export the most recent 50 sessions
- `--include-raw` also dump raw composer payloads and transcript files
- `--compact` write compact JSON instead of pretty printed JSON
- `--cursor-user-root <path>` override Cursor's `User` directory
- `--projects-root <path>` override the `.cursor\projects` directory

## Output shape

Each normalized session keeps:

- session metadata
- workspace links
- normalized messages
- tool events
- checkpoints
- request contexts
- transcript summaries

The output is designed for downstream agents, retrieval, and workflow analysis rather than direct human browsing.
