# org_contributor_pipeline

**在 Cursor 里使用的组织级贡献与能力证据工程**：Python 负责可重复 **事实与指标**，**分析、评级叙事与管理层表述由 Cursor Agent（+ 人）完成**，不把流水线做成「纯脚本出终判」。

## 为何不是纯脚本

- 能力判断依赖 **岗位、分工、投入时间、产出是否存在**；无产出须 **待评**，不能由 cron 填 C/D。  
- 「维度档 / 综合结论 / 是否淘汰」需要对齐组织量表（如老板定义的 A/B/C/D 语义），适合在对话里迭代、留痕、由人确认。

## Cursor 里怎么用

1. 打开 **本仓库根目录**（以加载 `.cursor/rules/org-contributor-pipeline.mdc` 与根目录 **`AGENTS.md`**）。  
2. 阅读 **`AGENTS.md`**（本目录下）：分工、推荐对话流程、禁止项。  
3. 在 Chat / Agent 中按 `prompts/README.md` 分阶段引用 **`prompts/*.md`**，并附上流水线产出的 JSON artifact 或节选。

### 用 Cursor CLI（`agent`）执行

适合定时或脚本里触发 **Ask 模式研判**（默认不改仓库文件）：

- 说明与示例命令：**`docs/CURSOR_CLI.md`**  
- 单阶段：**`scripts/run_cursor_stage.ps1`**（`-Stage`、可选 `-ArtifactPath`）  
- **一键三阶段 + Markdown 报告**：**`scripts/run_automated_stages.ps1`**（先 `python -m org_contributor_pipeline.emit_demo_artifact` 生成演示 artifact，再依次跑阶段 1～3，报告在 `artifacts/reports/stage-{1,2,3}-*.md`）  
- 仅生成演示数据（无 AI）：**`org-contributor-emit-demo`** 或 `python -m org_contributor_pipeline.emit_demo_artifact`
- **GitLab 全组 ingest + 三阶段**：在仓库根配置 **``.env``**（已 ``.gitignore``），例如 ``GITLAB_TOKEN=...``、``GITLAB_URL=https://gitlab.fingergame.com``；若 401 且确认 token 有效，可试 ``GITLAB_AUTH=bearer``（少数 OAuth/实例令牌需 Bearer 头）。然后：

  ```powershell
  .\org_contributor_pipeline\scripts\run_gitlab_full.ps1
  ```

  或手动：

  ```powershell
  python -m org_contributor_pipeline.ingest.gitlab_commits `
    --group "h5_game_sh_tpe" `
    --since "2026-03-01T00:00:00Z" `
    --until "2026-05-11T00:00:00Z" `
    -o org_contributor_pipeline/artifacts/generated/gitlab_group_ingest.json
  ```

  （ingest 启动时会自动加载根目录 ``.env``；也可用 ``.secrets/gitlab_token`` 或 ``--token-file`` / ``GITLAB_TOKEN_FILE``。）

  GitLab 的 `until` 为**不包含**该时刻；建议把 `--until` 设为窗口**次日** `T00:00:00Z`。  
  **建议 enrich 顺序（按需删减）**：`merge_evaluation_scope` → 可选 **`enrich_repo_catalog`**（`meta.repo_catalog`：clone URL + `recent_shas`，流水线不 clone）→ 可选 **`enrich_commit_diffs`**（截断 diff）→ **`enrich_artifact --plugin all --replace`** → 三阶段；**ArtifactPath** 指向最终 JSON。  
  若仍写旧顺序：先 `enrich_artifact` 再 `merge_evaluation_scope` 亦可，但 **repo_catalog / commit_diff 须在 merge 之后、三阶段之前** 写入同一 artifact 才便于 Agent 一次读取。  
  可选：`python -m org_contributor_pipeline.scope_audit -i <artifact.json>` 检查必评人是否在窗口内有 Git 样本（结果 JSON 打印到 stdout）。  
  **CI 自检（自动判断）**：`python -m org_contributor_pipeline.verify_pipeline` — `compileall` + demo 全插件链路 +（若存在 `gitlab_group_artifact_scoped.json`）必评 8 人 Git 覆盖；失败 `exit 1`。  
  示例（三阶段请指向 **已 enrich + 已 merge 评估范围** 的 JSON，勿用裸 ingest 以免缺插件与必评名单）：  
  `.\org_contributor_pipeline\scripts\run_automated_stages.ps1 -SkipEmit -ArtifactPath org_contributor_pipeline\artifacts\generated\gitlab_group_artifact_scoped.json`

  可选：`--dry-run`、`--all-branches`、`--include-project-regex`、`--exclude-project-regex`。

仓库根已增加 **`AGENTS.md`**，便于 CLI 与编辑器一致加载顶层约定。

## Python 包布局

| 路径 | 职责 |
|------|------|
| `models/` | `CommitEvent`、`PluginResult` 等 **给 AI 读的结构化事实** |
| `rubric/` | `dimensions.json`（两级维度）；`evaluation_scope.json`（必评人）；**`review_framework.json`（必审三大 L1 + 证据口径，非仅靠插件）** |
| `plugins/` | `PipelinePlugin` 与纯函数 runner：`delivery_traceability`（`vcs_footprint`）、`commit_title_signals`（标题关键词代理）、`path_taxonomy_proxy`（仓路径粗分）、`identity_footprint`（归因/分片置信度）；均仅消费 `commit_events` |
| `enrich_artifact.py` | CLI：对已有 artifact 追加 `plugin_results`（例：`org-contributor-enrich-artifact`） |
| `enrich_repo_catalog.py` | 写入 ``meta.repo_catalog``：每仓 ``clone_url_https``、可选 ``default_branch``、``recent_shas`` 取样；**不 clone**（`org-contributor-enrich-repo-catalog`） |
| `merge_evaluation_scope.py` | 将 `evaluation_scope.json` 与 `review_framework.json` 写入 artifact `meta`（`org-contributor-merge-evaluation-scope`） |
| `scope_audit.py` | 校验必评名单与 `commit_events` 覆盖（`org-contributor-scope-audit`；摘要 JSON 输出到 stdout） |
| `verify_pipeline.py` | **一键自检**：`compileall` + demo 链路 +（若存在）`gitlab_group_artifact_scoped.json` 必评严格覆盖；**退出码 0/1 自动判断**（`org-contributor-verify-pipeline`） |
| `env_loader.py` | 从仓库根 **`.env`** 加载配置到进程环境（ingest / emit 入口会先调用） |
| `ingest/` | GitLab REST：`ingest/gitlab_commits.py`（读 ``GITLAB_TOKEN`` / ``GITLAB_URL`` 等，可与根目录 **``.env``** 配合） |
| `orchestrator/` | 调度与插件注册（实现中） |

## 与 `cursor_agent_memory` 的关系

同仓库并列子项目：前者偏 Cursor 本地会话导出；本目录偏 **GitLab 多仓贡献事实 + Cursor 内研判工作流**。

### 对已有 artifact 追加插件（示例）

```powershell
python -m org_contributor_pipeline.enrich_artifact `
  -i org_contributor_pipeline/artifacts/generated/gitlab_group_ingest.json `
  -o org_contributor_pipeline/artifacts/generated/gitlab_with_delivery.json `
  --plugin all --replace
```

单跑某一插件（与旧行为一致）：`--plugin delivery_traceability`；追加前去掉该插件旧行：`--replace`。

### 拉取提交代码 diff（patch 级事实）

ingest **只拉提交列表元数据**；要对 **unified diff 片段** 做阶段 2/3，须对已含 `meta.evaluation_scope` 的 artifact 再跑（**会大量请求 GitLab API**，请用 cap / 必评人过滤控量）：

```powershell
python -m org_contributor_pipeline.enrich_commit_diffs `
  -i org_contributor_pipeline/artifacts/generated/gitlab_group_artifact_scoped.json `
  -o org_contributor_pipeline/artifacts/generated/gitlab_group_with_diffs.json `
  --only-evaluation-scope-persons --max-commits 400 --max-per-person 30
```

再对该输出跑 `enrich_artifact --plugin all`（若尚无插件）、最后跑三阶段；**ArtifactPath** 指向含 `commit_diff` 的 JSON。`--skip-existing-ok` 可断点续跑。

### 仓库克隆提示（轻量，不自动 clone）

在含 ``meta.gitlab_base_url`` 的 artifact 上生成 **每仓 HTTPS（及可选 SSH）clone 地址** + **最近提交 sha 取样**（全量仍在 ``commit_events``）：

```powershell
python -m org_contributor_pipeline.enrich_repo_catalog `
  -i org_contributor_pipeline/artifacts/generated/gitlab_group_with_diffs.json `
  -o org_contributor_pipeline/artifacts/generated/gitlab_group_with_hints.json `
  --url-style https --max-shas-per-project 24
```

可选 ``--fetch-default-branch``（需 token）填充默认分支。**Agent** 在本地有权限时 **自行决定** 克隆哪些仓、是否 ``--depth 1``、检出哪些 ``sha``；流水线不代劳全组 clone。

## 依赖

由仓库根 `pyproject.toml` 统一安装：`pip install -e .`（包名仍为 `cursor-agent-memory`，但会包含 `org_contributor_pipeline`）。
