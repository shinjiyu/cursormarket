# 使用 Cursor CLI 驱动本流水线（研判层）

Python 部分产出 artifact 后，可用 **Cursor Agent CLI** 在非交互/半自动场景跑 **阶段提示词**（`prompts/*.md`），与在编辑器里 Chat 等价：会加载 **仓库根** 的 `.cursor/rules`、`AGENTS.md`，以及（若配置）`mcp.json`。

官方说明：[Using Agent in CLI](https://cursor.com/docs/cli/using)、[Headless CLI](https://cursor.com/docs/cli/headless)。

## 认证：能复用「现在已在 Cursor 里登录」的状态吗？

**不完全是「同一进程里的登录态」**，但可以是**同一 Cursor 账号**，两种方式：

| 方式 | 说明 |
|------|------|
| **`agent login`（推荐本机）** | 走浏览器登录一次；凭证会**落在本机**供 CLI 使用（见 [Authentication](https://cursor.com/docs/cli/reference/authentication)）。与桌面版是否已登录**不是同一块内存**，但用同一账号完成 `agent login` 后，日常在终端跑 `agent -p` 一般不必再登。 |
| **`CURSOR_API_KEY` / `--api-key`** | 适合脚本/CI：在 Dashboard → Integrations 创建 API Key；与 IDE 里「已登录」也是**独立配置**，只是同属你的账号。 |

结论：**不能指望「只打开过 Cursor 桌面」就自动让 `agent` 已登录**；需要至少一次 **`agent login`** 或设置 **`CURSOR_API_KEY`**。完成后，本仓库脚本即可在非交互环境调用 `agent -p`。

## 一键自动化（本机 / 计划任务）

在仓库根：

```powershell
.\org_contributor_pipeline\scripts\run_automated_stages.ps1
```

- 会生成 `org_contributor_pipeline/artifacts/generated/demo_pipeline_input.json`（演示数据，可换成真实 ingest 输出路径）。  
- 依次执行阶段 1～3，输出写入 `org_contributor_pipeline/artifacts/reports/stage-*.md`（**UTF-8 无 BOM** Markdown；已避免 `Tee-Object` 在 Windows PowerShell 5.x 下默认写 UTF-16 导致用 UTF-8 打开乱码）。  
- 已登录 CLI：`agent login`；脚本已带 `--trust` 以通过 Workspace Trust。

仅重跑 AI、不重生成 JSON：

```powershell
.\org_contributor_pipeline\scripts\run_automated_stages.ps1 -SkipEmit
```

## 前置条件

1. 已安装 Cursor CLI，终端中能执行 **`agent`**。  
2. 已 **`agent login`** 或设置 **`CURSOR_API_KEY`**（见上文「认证」）。  
3. 在 **本仓库根目录** 下执行脚本，或使用 **`--workspace`** 指向仓库根。

## 推荐：`--mode=ask` + `--print`

研判阶段默认 **不要求改仓库文件**，用 Ask 模式避免误写代码：

```powershell
cd D:\tools\cursorLogViewer
agent -p --mode=ask --workspace "D:\tools\cursorLogViewer" @"
请完整执行 org_contributor_pipeline/prompts/01_identity_and_scope.md 中的任务。
用户会在下一条消息粘贴 artifact；若当前消息中已包含 JSON 片段，请先基于该片段作答。
不要修改任何源文件，只输出分析结果。
"@
```

将 artifact（或 `artifacts\*.json` 路径）写进提示里，或使用包装脚本自动拼接（见 `scripts/run_cursor_stage.ps1`）。

## 输出格式

- 日志/自动化解析：`--output-format json` 或 `stream-json`（见 CLI Output format 文档）。  
- 人类阅读：`--output-format text`（默认）。

## 与 MCP

CLI 会读取用户级 **`mcp.json`**；若研判过程需要接内部 GitLab MCP 等，与在 IDE 中一致配置即可。

## 与「纯脚本」的边界

- **允许**：`agent -p` 调用 AI 做阶段 1～3 的叙事、对齐量表、产出 Markdown 报告正文（可再重定向到文件）。  
- **不建议**：在无人审核的 CI 里自动把 CLI 输出当作「最终绩效/淘汰」依据；应写入草稿并由人确认。

## 包装脚本

- **`scripts/run_cursor_stage.ps1`** / **`run_cursor_stage.sh`**：单阶段。  
- **`scripts/run_automated_stages.ps1`**：生成演示 artifact + 阶段 1～3 + 日志。
