# Cursor MCP Directory submission packet

Everything you need to copy/paste into a directory submission form (Cursor's
in-app MCP browser, modelcontextprotocol.io's "awesome-mcp" lists,
Smithery, mcp.so, etc.). Replace placeholder URLs once the package is
published.

> Note: Cursor does not (yet) run a public submission portal at the time of
> writing. The fields below are written so they map cleanly to whatever
> intake form a future directory uses.

---

## Identity

| Field | Value |
|---|---|
| **Name** | Cursor Agent Memory |
| **Slug** | `cursor-agent-memory` |
| **Tagline** (≤ 80 chars) | Share Cursor sessions across every Cursor window via a local MCP. |
| **Tagline (zh)** | 让本机所有 Cursor 窗口共享同一份会话记忆，零网络。 |
| **Author / handle** | shinjiyu |
| **License** | MIT |
| **Source** | https://github.com/shinjiyu/cursormarket |
| **Issues** | https://github.com/shinjiyu/cursormarket/issues |
| **Package (PyPI)** | https://pypi.org/project/cursor-agent-memory/ *(post-publish)* |
| **Categories / tags** | `productivity`, `developer-tools`, `local-first`, `cursor`, `memory`, `search` |
| **Runtime** | Python 3.10+ |
| **Transport** | stdio |
| **Platforms** | Windows, macOS, Linux |

---

## Short description (≤ 280 chars, English)

> Reads your local Cursor sessions (the global state DB, every workspace, and `.cursor/projects/.../agent-transcripts`) into a normalized JSON tree, and exposes that tree to **any Cursor window on the same machine** as a stdio MCP. Everything stays local; nothing is sent to the cloud.

## Short description (≤ 280 chars, 中文)

> 把本机 Cursor 的全局状态、各 workspace 存储、以及每个项目的 `agent-transcripts` 统一导出成标准化 JSON 树，再通过 stdio MCP 暴露给本机**任意一个 Cursor 窗口**。**全程本地，不联网**。

---

## Long description (markdown, English)

```markdown
**The pitch**

Cursor remembers the conversation you're in, but every workspace lives in its
own bubble. The session that finally got that gnarly bug fixed last week is
buried inside one specific `.cursor/projects/<id>/agent-transcripts/…`
folder, and AI agents in Cursor have no clean way to *grep your own Cursor
history* the way you would grep your shell history.

`cursor-agent-memory` fixes this with two small pieces:

1. A **local exporter** that reads Cursor's global `state.vscdb`, every
   workspace's storage, and every project's transcripts into one normalized
   JSON tree.
2. A **stdio MCP server** that exposes that tree to any Cursor window with
   six obvious tools.

A scheduled sync keeps the export folder fresh in the background. Nothing
ever leaves the machine.

**Tools exposed**

- `cursor_logs_export_dir` — where exports live on disk
- `cursor_logs_read_manifest` — sync summary
- `cursor_logs_list_sessions` — recent sessions (title / workspace / tools)
- `cursor_logs_search_sessions` — substring search across title / id / workspace
- `cursor_logs_get_session` — full normalized JSON for one session
- `cursor_logs_read_workspaces` — discovered workspaces

You don't usually call these by name; the agent picks them based on what you
ask in plain language.

**Try it**

```bash
pip install cursor-agent-memory
cursor-agent-memory-sync --once
```

Then add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "cursor-agent-memory-logs": {
      "command": "cursor-agent-memory-mcp"
    }
  }
}
```

Restart Cursor; in chat: `@` → MCP → `cursor-agent-memory-logs`, then ask
*"find the session where I was debugging the WebSocket reconnect loop last
week and summarize what we tried."*

**Privacy posture**

- Pure local. No outbound HTTP from the exporter or the MCP server.
- The exporter only reads files Cursor already writes to disk.
- The export folder contains your conversations and code snippets in plain
  JSON. Treat it like shell history; don't sync it to a public Git repo.
```

## Long description (markdown, 中文)

```markdown
**推广要点**

Cursor 单个窗口里的对话很好用，但跨工作区没法互通：今天上午在 A 工程里调通的
那个 bug，下午切到 B 工程就找不回来了；那段被埋在
`~/.cursor/projects/<id>/agent-transcripts/` 里的关键会话，靠目录翻几乎不可能找到。

`cursor-agent-memory` 用两个小东西解决这件事：

1. **本地导出器**：把 Cursor 的全局 `state.vscdb`、每个 workspace 存储、以及
   `~/.cursor/projects/*/agent-transcripts/*` 全读出来，写成一份干净、标准化的
   JSON 树。
2. **stdio MCP 服务**：把这个目录暴露给本机**任意一个 Cursor 窗口**，提供
   6 个直白的工具（list / search / get / read_workspaces / 等）。

后台定时同步保持目录新鲜。**全程本地，不联网。**

**60 秒安装**

```bash
pip install cursor-agent-memory
cursor-agent-memory-sync --once
```

把这段加到 `~/.cursor/mcp.json` 的 `mcpServers`：

```json
{
  "mcpServers": {
    "cursor-agent-memory-logs": {
      "command": "cursor-agent-memory-mcp"
    }
  }
}
```

重启 Cursor，在任意对话里 `@` → MCP → `cursor-agent-memory-logs`，然后用大白
话问：

> "找到上周我在调 WebSocket 重连那次会话，总结一下我们试了哪些方案。"
```

---

## Install snippet (one-liner, for "how do I add this?" docs)

**Windows / macOS / Linux:**

```bash
pip install cursor-agent-memory && cursor-agent-memory-sync --once
```

**MCP config:**

```json
{
  "mcpServers": {
    "cursor-agent-memory-logs": {
      "command": "cursor-agent-memory-mcp"
    }
  }
}
```

---

## Screenshots / assets to upload (TODO)

Replace these with real captures before submitting. Suggested set, in order:

1. **Hero**: Cursor chat with `@cursor-agent-memory-logs` selected and a
   natural-language query that returns a previous session.
2. **Tool list**: the MCP tools panel showing the 6 tools and their
   descriptions.
3. **The exported JSON tree** in any file explorer, showing
   `~/.cursor-agent-memory/export/normalized/sessions/*.json`.
4. **Cross-window demo**: two Cursor windows side by side, both pulling from
   the same memory.

Suggested image dimensions for most directories: 1280×720 PNG.

Logo: TODO. A simple monochrome glyph (square brain / file stack / chat
bubble with arrow) renders well at small sizes; 512×512 PNG with transparent
background is the safest baseline.

---

## Submission targets (with checklists)

### Cursor in-app MCP browser

- [ ] Confirm the directory exists / opens for community submissions
- [ ] Submit name, tagline (≤ 80c), short description (≤ 280c), install
      snippet, source URL, license

### `awesome-mcp-servers` (modelcontextprotocol.io / GitHub)

- [ ] PR adding an entry under "Community / Productivity":
      `* [cursor-agent-memory](https://github.com/shinjiyu/cursormarket) — Share local Cursor sessions across every Cursor window via a stdio MCP.`

### Smithery (smithery.ai)

- [ ] Create a `smithery.yaml` if/when registering (uses the same
      `command` + `env` shape as `mcp.json`)

### mcp.so / glama.ai / pulsemcp.com

- [ ] Each accepts a Git URL + tagline + tags. Reuse the fields above.

---

## Pre-submission checklist

- [ ] PyPI package is live (`pip install cursor-agent-memory` works clean)
- [ ] Repo has a `LICENSE` (MIT, included in this repo at `/LICENSE`)
- [ ] README badges: install, version, license, downloads (post-PyPI)
- [ ] At least 1 hero screenshot or short GIF
- [ ] An issue template + a SECURITY.md note that it's local-only
- [ ] `examples/run_demo.py` works on a clean machine without any Cursor
      history
- [ ] Tagged a `v0.1.0` GitHub Release with the wheel + sdist attached
