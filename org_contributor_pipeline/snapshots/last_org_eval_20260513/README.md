# 入库快照（2026-05-13）

本目录为「最后一次 GitLab 范围扫描 + 必评 8 人正式 CLI 填分」的固定产物，便于 `hutao`/Git 追溯；流水线日常产出仍写在 `artifacts/generated/` 与 `artifacts/reports/`（默认被 `.gitignore` 忽略）。

| 文件 | 说明 |
|------|------|
| `gitlab_group_artifact_scoped.json` | 带 `evaluation_scope` 的 scoped artifact（扫描入库） |
| `evaluation_run-demo-scoped.json` | 由此 artifact 生成的 `evaluation_run.v1` 基线 |
| `evaluation_run-demo-scoped-scored.json` | `cursor agent_cli` 合并后的打分结果 |
| `evaluation_run-demo-scoped-scored.md` | 由 `evaluation_run_to_markdown` 导出的可读报告 |
| `evaluation_run-demo-scoped.fill-scores.prompt.txt` | Step 4 侧车提示（超长 argv 时） |
| `evaluation_run-demo-scoped.json.fill-scores.log` | Agent 标准输出日志 |
