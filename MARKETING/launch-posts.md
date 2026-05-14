# Launch posts — `cursor-agent-memory`

Ready-to-post copy for the platforms most likely to actually convert into
installs. Each variant is sized for the channel and avoids hype words
("revolutionary", "game-changer") that get downranked on dev forums.

Replace `https://github.com/shinjiyu/cursormarket` with the canonical URL if
the repo moves before launch.

---

## X / Twitter (English) — 270 chars

> Built a tiny MCP that lets all your Cursor windows share the same
> "session memory."
>
> It exports the global state DB, every workspace, and your
> `agent-transcripts/` into one folder, then serves it over a local stdio
> MCP. No cloud. No daemons phoning home.
>
> `pip install cursor-agent-memory`
>
> https://github.com/shinjiyu/cursormarket

## X / Twitter (中文) — 138 字

> 写了个本地 MCP：让你本机所有 Cursor 窗口共享同一份「会话记忆」。
>
> 把 Cursor 的全局状态、各 workspace 存储、每个项目的 agent-transcripts 都
> 同步到一个文件夹，再用 stdio MCP 暴露给任意 Cursor 窗口。**全程本地，
> 不联网。**
>
> `pip install cursor-agent-memory`
>
> https://github.com/shinjiyu/cursormarket

---

## Hacker News (Show HN) — title + first comment

**Title (≤ 80 chars):**

> Show HN: cursor-agent-memory – share Cursor sessions across windows via a local MCP

**First comment (signed, factual; HN dislikes marketing tone):**

> Author here. I kept hitting the same friction in Cursor: the conversation
> that solved a tricky bug last week is buried inside one specific
> workspace's `.cursor/projects/<id>/agent-transcripts/…` and there's no
> good way to find it from a different window.
>
> This is two small pieces:
>
> 1. A local exporter that walks Cursor's global `state.vscdb`, every
>    workspace's storage, and the per-project transcript files, and writes
>    a normalized JSON tree to one folder.
> 2. A stdio MCP server that exposes that folder to any Cursor window with
>    six obvious tools (`list_sessions`, `search_sessions`, `get_session`,
>    etc.).
>
> A scheduled sync keeps the folder fresh. Nothing leaves the machine. The
> exporter is read-only against Cursor's files; the MCP server makes no
> network calls.
>
> Install:
>
>     pip install cursor-agent-memory
>     cursor-agent-memory-sync --once
>
> Then add the snippet from the README to `~/.cursor/mcp.json` and restart
> Cursor.
>
> Tested on Windows 10 and a fresh macOS dev box; Linux paths are wired up
> but I haven't shipped it to anyone using Linux as a daily driver yet, so
> bug reports there are very welcome.
>
> What I'd genuinely like feedback on:
>
> - Whether the JSON shape per session is useful for retrieval / RAG
>   downstream, or whether I should bias it more toward "human readable
>   markdown chunks."
> - Whether the MCP tool surface is the right granularity (six tools) vs.
>   collapsing into one omnibus `query()` tool with a small DSL.

---

## Reddit — `r/cursor` and `r/LocalLLaMA`

**Title:**

> Made a local MCP so all my Cursor windows can finally see each other's
> chat history

**Body:**

> One thing I kept tripping on with Cursor: every workspace is its own
> bubble. Today I'm in workspace A; tomorrow I'm in workspace B; the
> session where I actually worked out a fix is invisible from anywhere
> except the window I happened to open it in.
>
> So I wrote a small thing:
>
> - **Exporter** reads Cursor's global state DB + every workspace storage +
>   `~/.cursor/projects/*/agent-transcripts/*` into a normalized JSON tree
>   at `~/.cursor-agent-memory/export/`.
> - **stdio MCP server** exposes that tree to any Cursor window via 6 tools
>   (list / search / get-by-id / etc.).
> - **Scheduled sync** keeps it fresh.
> - **No cloud.** The MCP server makes zero network calls; the exporter
>   only reads files Cursor already writes locally.
>
> Install:
>
>     pip install cursor-agent-memory
>     cursor-agent-memory-sync --once
>
> Then drop this in `~/.cursor/mcp.json` and restart Cursor:
>
>     {
>       "mcpServers": {
>         "cursor-agent-memory-logs": {
>           "command": "cursor-agent-memory-mcp"
>         }
>       }
>     }
>
> In any chat: `@` → MCP → `cursor-agent-memory-logs`, then ask in plain
> language: *"find the session where I was debugging the websocket
> reconnect loop and summarise what we tried."*
>
> MIT, source: https://github.com/shinjiyu/cursormarket
>
> Genuinely interested in:
>
> - Linux edge cases (paths are coded but I've only smoke-tested macOS +
>   Windows).
> - Whether you want one big `query()` tool with a small DSL instead of the
>   current 6-tool surface.

---

## 掘金 / 思否 / V2EX (中文长文骨架)

**标题：**

> 给 Cursor 写了个 MCP：让本机所有窗口共享同一份"会话记忆"，全程本地

**开头钩子（150 字，给 V2EX/X 直接用）：**

> Cursor 单个窗口的对话很顺，但跨窗口完全不通：上周在 A 工程里调通的那次，
> 想在 B 工程引用，靠人去翻 `~/.cursor/projects/.../agent-transcripts/` 几乎
> 不可能。
>
> 写了个 `cursor-agent-memory`：把 Cursor 的全局 state、各 workspace 存储、
> 每个项目的 transcript 全导出到一个目录，再用本地 MCP 暴露给本机任意一个
> Cursor 窗口。
>
> 全程本地、不联网。`pip install cursor-agent-memory` 就能用。
>
> 仓库：https://github.com/shinjiyu/cursormarket

**正文骨架（适合掘金/思否长文）：**

```markdown
## 这玩意儿想解决的问题

[一段：举一个具体的"我去年调通的那个 bug 在哪"场景，最好带截图]

## 拆开看是两件小事

1. **本地导出器**：读 Cursor 的全局 `state.vscdb`、各 workspace 存储、
   `~/.cursor/projects/*/agent-transcripts/*`，统一写成 JSON 树。
2. **stdio MCP 服务**：把这个目录暴露给本机任意 Cursor 窗口，提供 6 个工具
   （list / search / get / read_workspaces / read_manifest / export_dir）。

[一张架构图，README 里的 ASCII 图直接转成图片]

## 60 秒装上

[贴 README 的 install 段]

## 它不会做什么

- 不联网，不上传任何东西
- 不动 Cursor 自己的文件，只读
- 不替你做 RAG / 不存向量索引（就是个干净的 JSON 树，下游想做啥都行）

## 我希望听到的反馈

- Linux 路径有没有踩坑
- session JSON 的字段够不够，还缺什么
- 6 个工具的粒度，对 agent 来说是不是合适

仓库：https://github.com/shinjiyu/cursormarket  · MIT
```

---

## Slack / 飞书 / 钉钉 (内部群消息)

> 顺手做了个小工具想推给大家：
>
> Cursor 不同 workspace 之间没法共享会话记忆，我做了个本地 MCP 把这事补上：
> 后台同步导出全部本机 Cursor 会话 → 通过 stdio MCP 暴露给任意 Cursor 窗口
> → 在对话里 `@cursor-agent-memory-logs` 直接拿过去某次会话的内容做参考。
>
> 全程本地不联网，30 秒装好。
>
> 装法（任意 Python 3.10+ 环境）：
> `pip install cursor-agent-memory && cursor-agent-memory-sync --once`
>
> 然后把 README 里那段 mcp.json snippet 抄进 `~/.cursor/mcp.json`，重启
> Cursor 就能用。
>
> 仓库 + 安装/Demo：https://github.com/shinjiyu/cursormarket

---

## YouTube / 短视频脚本（30 秒）

```text
[0–3s]  屏幕里两个 Cursor 窗口并排开。
        旁白："Cursor 跨窗口看不到彼此的会话历史，对吧？"

[3–10s] 在 A 窗口里完成一段调试，关掉。
        切到 B 窗口。
        在 B 窗口里 @ MCP，输入："找到我刚刚在 A 工程调过的那段 WebSocket
        重连，复述一下结论。"

[10–18s] AI 立刻把刚才的会话拉过来，给出总结。
         字幕："本机 MCP，全程本地。"

[18–25s] 切到终端，pip install cursor-agent-memory + 一行同步。
         字幕："60 秒装好。"

[25–30s] GitHub 卡片 + 标语 "share Cursor sessions across every Cursor
         window."
```

---

## Posting order (suggested)

1. **Day 0**: GitHub Release v0.1.0 + PyPI publish.
2. **Day 0 evening (Asia)**: 掘金 / 思否长文 + V2EX 短贴。
3. **Day 1 morning (US)**: Show HN + r/cursor + r/LocalLLaMA.
4. **Day 1 afternoon (US/EU)**: X/Twitter thread (English short variant
   above, 1 reply with the install snippet, 1 reply with a 15s screen
   recording).
5. **Day 2**: PR to `awesome-mcp-servers` referencing the live repo +
   PyPI.
6. **Day 7**: Follow-up post citing a couple of real bug-report fixes that
   came back, asking for Linux daily-drivers specifically.
