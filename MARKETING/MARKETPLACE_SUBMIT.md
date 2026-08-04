# Cursor Marketplace — submit packet

Submit at: https://cursor.com/marketplace/publish  
Fallback contact: kniparko@anysphere.com

## Repository

- **GitHub**: https://github.com/shinjiyu/cursormarket
- **Plugin layout**: single plugin at repo root (`.cursor-plugin/plugin.json`)
- **License**: MIT

## Form fields (copy/paste)

| Field | Value |
|---|---|
| Plugin name | Cursor Agent Memory |
| Plugin slug / name | `cursor-agent-memory` |
| Tagline | Share Cursor sessions across every Cursor window via a local MCP. |
| Short description | Reads local Cursor sessions into a normalized JSON tree and exposes them to any Cursor window on the same machine via stdio MCP. Local-only; no cloud. |
| Categories / tags | productivity, developer-tools, local-first, mcp, memory |
| Runtime | Python 3.10+ (launched with `uvx`) |
| Homepage | https://github.com/shinjiyu/cursormarket |

## What reviewers should see

1. `.cursor-plugin/plugin.json` — manifest
2. `mcp.json` — `uvx --from cursor-agent-memory cursor-agent-memory-mcp`
3. `skills/cross-workspace-session-memory/SKILL.md` — when/how to use tools
4. `assets/logo.svg` — logo
5. `README.md` — install + privacy
6. `SECURITY.md` — local-only posture
7. PyPI: https://pypi.org/project/cursor-agent-memory/

## Pre-submit checklist

- [ ] PyPI package live (`uvx --from cursor-agent-memory cursor-agent-memory-mcp` starts)
- [ ] Plugin files committed and pushed to `main`
- [ ] Local smoke: symlink repo to `~/.cursor/plugins/local/cursor-agent-memory`, Reload Window, MCP green
- [ ] One-shot sync documented / works: `uvx --from cursor-agent-memory cursor-agent-memory-sync --once`
- [ ] Optional screenshots under `marketing/screenshots/` (hero chat + tools panel)

## Do not submit in this plugin scope

- `org_contributor_pipeline/` (separate product; ignore for review narrative)
- Optional web hub is documented as optional only
