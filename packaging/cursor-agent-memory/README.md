<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <strong>cursor-agent-memory</strong>
</p>

<p align="center">
  Share local Cursor sessions across every Cursor window — via a tiny MCP server.
  <br/>
  把本机的 Cursor 会话历史，跨所有 Cursor 窗口共享出去 — 通过一个轻量 MCP 服务。
</p>

<p align="center">
  <a href="#install-in-60-seconds-windows--macos--linux">Install</a> ·
  <a href="#what-it-does">What it does</a> ·
  <a href="#mcp-tools">MCP tools</a> ·
  <a href="#try-the-demo-without-touching-your-real-cursor-data">Demo</a> ·
  <a href="#中文说明">中文</a>
</p>

---

## Why

Cursor is great at remembering **the conversation you're in**, but every workspace lives in its own bubble:

- The work you did in workspace A this morning is invisible to workspace B this afternoon.
- The session that finally got that gnarly bug fixed last week is buried inside one specific `.cursor/projects/<id>/agent-transcripts/…` folder.
- AI agents in Cursor have no clean way to *grep your own Cursor history* the way you would `grep` your shell history.

`cursor-agent-memory` does two small things that, together, fix this:

1. A **local exporter** that reads Cursor's per-user state (the global `state.vscdb`, every workspace's storage, and `.cursor/projects/*/agent-transcripts`) and writes a clean, normalized JSON tree to one folder you choose.
2. A **stdio MCP server** that exposes that folder to **any Cursor window on the same machine** as a handful of obvious tools (`list_sessions`, `search_sessions`, `get_session`, …).

A scheduled sync keeps the export folder fresh in the background. The MCP doesn't talk to the cloud; everything stays on your laptop.

> Not affiliated with Cursor or Anysphere. Reads files Cursor already writes locally.

---

## What it does

```
                ┌────────────────────────────────────┐
                │  Your local Cursor                 │
                │  - %APPDATA%\Cursor\User\…  (Win) │
                │  - ~/Library/.../Cursor/User (mac) │
                │  - ~/.config/Cursor/User    (lin) │
                │  - ~/.cursor/projects/.../        │
                │      agent-transcripts/*           │
                └─────────────────┬──────────────────┘
                                  │
                  cursor-agent-memory-sync (every N minutes)
                                  │
                                  ▼
                    ~/.cursor-agent-memory/export/
                    ├── manifest.json
                    ├── normalized/
                    │     ├── workspaces.json
                    │     ├── session_index.json
                    │     └── sessions/<safe_id>.json
                    └── raw/   (optional, --include-raw)
                                  │
                                  │  stdio MCP
                                  ▼
                ┌────────────────────────────────────┐
                │  Any Cursor window on this machine │
                │  ↳ @cursor-agent-memory-logs       │
                │     "find the session where I…"    │
                └────────────────────────────────────┘
```

---

## Cursor Marketplace (recommended)

After listing, install **Cursor Agent Memory** from **Customize → Marketplace**, then run a one-shot sync so the MCP has data:

```bash
uvx --from cursor-agent-memory cursor-agent-memory-sync --once
```

Manual / pre-Marketplace install is below. Plugin metadata lives in `.cursor-plugin/plugin.json` + root `mcp.json`.

## Install in 60 seconds (Windows / macOS / Linux)

> Requires Python 3.10+ and a recent Cursor. For one-click MCP without a global pip install, prefer `uvx` (see Marketplace section).

### Windows (PowerShell)

```powershell
# 1. install
pip install cursor-agent-memory

# 2. one-time export to populate the shared folder
cursor-agent-memory-sync --once

# 3. wire it into Cursor's mcp.json
$mcp = "$env:USERPROFILE\.cursor\mcp.json"
if (-not (Test-Path $mcp)) { '{ "mcpServers": {} }' | Out-File -Encoding utf8 $mcp }
# then add the snippet from "MCP config" below into mcpServers
```

### macOS / Linux (bash / zsh)

```bash
pip install cursor-agent-memory
cursor-agent-memory-sync --once

# add the MCP snippet below to ~/.cursor/mcp.json
```

### MCP config (paste into `~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "cursor-agent-memory-logs": {
      "command": "cursor-agent-memory-mcp"
    }
  }
}
```

If `cursor-agent-memory-mcp` is not on `PATH`, fall back to:

```json
{
  "mcpServers": {
    "cursor-agent-memory-logs": {
      "command": "python",
      "args": ["-m", "cursor_agent_memory.mcp_server"]
    }
  }
}
```

Restart Cursor. In any chat, type `@` → MCP → `cursor-agent-memory-logs`, then ask in plain language:

> *"Find the session where I was debugging the WebSocket reconnect loop last week and summarize what we tried."*

---

## Keep it fresh (background sync)

You don't want to remember to re-export. Run `cursor-agent-memory-sync` on a schedule:

**Windows — Task Scheduler one-liner:**

```powershell
$cmd = (Get-Command cursor-agent-memory-sync).Source
schtasks /Create /SC HOURLY /TN "cursor-agent-memory-sync" /TR "$cmd --once" /F
```

**macOS — launchd or just a `cron` line:**

```bash
( crontab -l 2>/dev/null; echo "0 * * * * $(command -v cursor-agent-memory-sync) --once" ) | crontab -
```

**Linux — systemd user timer or cron** (same as macOS).

Or just run it as a long-lived process: `cursor-agent-memory-sync --interval 1800`.

> The default export directory is `~/.cursor-agent-memory/export`. Override with `CURSOR_AGENT_MEMORY_EXPORT_DIR`.

---

## MCP tools

| Tool | Purpose |
|---|---|
| `cursor_logs_export_dir` | Where exports live on disk. |
| `cursor_logs_read_manifest` | Latest sync summary: counts, paths, generated-at. |
| `cursor_logs_list_sessions` | Recent sessions (`title`, `workspace_paths`, `updated_at`, `tools_used`). |
| `cursor_logs_search_sessions` | Substring match on title / session_id / workspace path. |
| `cursor_logs_get_session` | One full normalized session JSON; large payloads are auto-truncated. |
| `cursor_logs_read_workspaces` | All discovered workspaces and their links to sessions. |

You normally don't call these by name — Cursor's agent will pick them based on what you ask.

---

## Try the demo (without touching your real Cursor data)

```bash
git clone https://github.com/shinjiyu/cursormarket.git
cd cursormarket
python -m examples.run_demo
```

This builds a tiny synthetic export tree under `examples/demo-export/` and prints sample MCP tool calls against it, so you can see the shape of the data before pointing it at your own Cursor.

---

## Privacy

- Runs entirely on your machine. No network calls from the exporter or the MCP server.
- The exporter only reads files Cursor already writes to disk.
- The export folder contains **your conversations and code snippets** in plain JSON. Treat it like the rest of your shell history: don't sync it to a public Git repo.

---

## Useful flags

```text
cursor-agent-memory --output ./out/cursor-export
    --include-raw         also dump raw composer payloads + transcripts
    --limit 50            only the 50 most recently updated sessions
    --compact             compact JSON instead of pretty-printed
    --cursor-user-root    override Cursor's User directory
    --projects-root       override ~/.cursor/projects
    --lang en|zh          UI language
```

Same flags on `cursor-agent-memory-sync` (the daemon is just a loop around the exporter).

---

## Internal-library web app (optional, separate use case)

The same package ships a small FastAPI app for **publishing curated raw bundles to a local team library**, with login, plugins, audit, and a download flow. It is not required for the MCP cross-Cursor sharing above.

```bash
cursor-agent-memory-web   # http://127.0.0.1:8008
```

UI is bilingual (English by default, 中文 selectable in the top bar).

---

## Output shape

Each session under `normalized/sessions/<id>.json` keeps:

- session metadata (title, model, mode, timestamps, workspaces)
- normalized messages (role, text, code blocks, tool results)
- tool events (one row per tool call, with `tool_name`, `path`, `summary`)
- checkpoints, request contexts, transcript summaries

The shape is designed for downstream agents and retrieval, not for human browsing.

---

## License

MIT. See `LICENSE`.

Issues, PRs, and bug reports welcome — especially platform-specific edge cases on macOS and Linux.

---

## 中文说明

### 这是什么

**用一个小小的 MCP，让你本机所有 Cursor 窗口共享同一份"会话记忆"。**

Cursor 单个窗口里的对话很好用，但跨工作区没法互通：今天上午在 A 工程里调通的那个 bug，下午切到 B 工程就找不回来了；那段被埋在 `~/.cursor/projects/<id>/agent-transcripts/` 里的关键会话，靠目录翻几乎不可能找到。

`cursor-agent-memory` 做两件事：

1. **本地导出器**：把 Cursor 的全局 `state.vscdb`、每个 workspace 的存储、以及 `~/.cursor/projects/*/agent-transcripts/*` 都读出来，写成一份干净的、标准化的 JSON 树。
2. **stdio MCP 服务**：把这个目录暴露给本机任何一个 Cursor 窗口，提供 `list_sessions` / `search_sessions` / `get_session` 等几个直白的工具。

加上一个后台定时同步，导出目录就一直是新鲜的。**全程本地，不联网。**

### Cursor Marketplace（推荐）

上架后可在 **Customize → Marketplace** 安装 **Cursor Agent Memory**，然后跑一次同步：

```bash
uvx --from cursor-agent-memory cursor-agent-memory-sync --once
```

插件清单：`.cursor-plugin/plugin.json` + 根目录 `mcp.json`。

### 60 秒安装

```powershell
# Windows / macOS / Linux 都是同一套（用对应 shell）
pip install cursor-agent-memory
cursor-agent-memory-sync --once
```

把这段加到 `~/.cursor/mcp.json` 的 `mcpServers` 里：

```json
{
  "mcpServers": {
    "cursor-agent-memory-logs": {
      "command": "cursor-agent-memory-mcp"
    }
  }
}
```

重启 Cursor，在任意对话里 `@` → MCP → `cursor-agent-memory-logs`，然后用大白话问：

> "找到上周我在调 WebSocket 重连那次会话，总结一下我们试了哪些方案。"

### 后台保鲜

```powershell
# Windows: 加一个每小时跑一次的计划任务
$cmd = (Get-Command cursor-agent-memory-sync).Source
schtasks /Create /SC HOURLY /TN "cursor-agent-memory-sync" /TR "$cmd --once" /F
```

```bash
# macOS / Linux: 一行 cron
( crontab -l 2>/dev/null; echo "0 * * * * $(command -v cursor-agent-memory-sync) --once" ) | crontab -
```

或者长跑：`cursor-agent-memory-sync --interval 1800`。

默认导出目录 `~/.cursor-agent-memory/export`，可用 `CURSOR_AGENT_MEMORY_EXPORT_DIR` 覆盖。

### 隐私

完全本地运行，只读 Cursor 已经写在你磁盘上的文件，不发任何网络请求。导出目录包含你的对话和代码片段，请像对待 shell history 一样保护它，不要传到公开 Git 仓。

更详细安装、Demo、隐私和可选的 Web 内部库，请看上面的英文章节。
