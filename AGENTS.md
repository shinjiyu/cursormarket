# Monorepo — Agent 说明

本仓库包含两个主要方向：

1. **`cursor_agent_memory/`** — 本地 Cursor 会话导出、Web 内部库、MCP 等。  
2. **`org_contributor_pipeline/`** — 组织级 Git 贡献事实 + **在 Cursor（含 CLI）里由 AI 做研判**；请勿单靠脚本输出人事终判。

使用 **Cursor CLI**（`agent -p`）时，请在 **本仓库根目录** 作为 `--workspace` 运行，以便加载 `.cursor/rules` 与本文件。详细命令见 **`org_contributor_pipeline/docs/CURSOR_CLI.md`**。若研判 **org_contributor_pipeline** 产出的 artifact 且需读实现，可结合 **`meta.repo_catalog`** 在本地按需 `git clone`（见该子目录 **`AGENTS.md`**）。
