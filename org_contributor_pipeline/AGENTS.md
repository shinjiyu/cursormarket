# AGENTS — org_contributor_pipeline

本工程在 Cursor 中的定位：**脚本/插件负责「事实层」，Agent 负责「研判层」**。二者不可拆成「只跑脚本就交卷」。

## 最简理解：你要的只有三步

你要的流程可以想成 **固定顺序的两步 + 一个增量开关**，和「插件名、schema」无关也能记住：

1. **第一步 — 用规则拿数据（统计 + 能拿到的代码片段）**  
   跑 GitLab 拉取、插件、`enrich_commit_diffs` 等，得到 **artifact**；再跑  
   `python -m org_contributor_pipeline.emit_evaluation_run -i <artifact.json> -o evaluation_run.json`  
   得到一份 **JSON**：里面每人有 **`facts`**（数字、路径、diff 摘要等），以及 **`mandatory_l2_scores`** 里每个二级维度一行 —— 此时 **分数那一列是空的**（还没评）。

2. **第二步 — 用 LLM 打分**  
   把 **同一份 `evaluation_run.json`（或 artifact 路径 + 提示词）** 交给大模型（例如按 `prompts/03_rubric_alignment.md`），让它根据 `facts` 和证据规则，**往 `mandatory_l2_scores` 里填 `grade` / `confidence` / `narrative_zh`**。  
   这一步 **不是** 仓库里另一段 Python 自动算分，就是 **LLM 读材料写字**。

3. **增量（可选）**  
   以后有新提交、重新生成了 **新 artifact** 时：  
   - 若资料够、你已有上一版打好分的 `evaluation_run.json`，可以用  
     `--run-kind incremental --baseline-json <上一版.json>`  
     **统计会全部用新 artifact 重算**；上一版里 **已经填过的分** 可以按规则合并进来（具体见下文「网页展示用 JSON」一节）。  
   - 若资料仍不够稳定打分，JSON 里会把 **下一步标成仍要先全量**，不会误用「半吊子增量」。

4. **第四步 — 研判层填分（LLM；本仓库默认定轨到 Cursor CLI `agent`）**  
   **LLM 在哪发生**：由 **`cursor agent`**（或你在 Cursor 里手动跑同一份提示词）读 `evaluation_run.v1` + `04_fill_evaluation_run_scores.md`，在模型里完成推理，**stdout 里吐出** `evaluation_run_scores_patch.v1`，再由 Python **合并**进基线 → `<stem>-scored.json`。Python **不算分、不调 OpenAI API**；没有 agent（也没有别处接模型）就没有研判层。  
   推荐用 Python 子进程写日志，避免 PowerShell 管道编码弄坏 JSON：  
   `python -m org_contributor_pipeline.run_fill_evaluation_scores -e <evaluation_run.json> -w <仓库根>`（可加 `--timeout-seconds 0` 长任务不设限；**建议加 ``--embed-evaluation-json``**，把整份 eval 放进 spool 提示，减少 agent 反复读盘。）  
   **仅结构/联调占位（无 LLM、无 CLI）**：`--stub` / `merge_evaluation_scores --stub-from-base` / `demo_evaluation_run_scored` 只写 **`pipeline_stub`** 占位分，**不能**代替上述 agent；占位须再由 agent 或人工产出真 patch 后重合并。  
   **缩小必评人数再跑 CLI（验通路）**：`python -m org_contributor_pipeline.slice_evaluation_run_people -i <大.json> -o <小.json> -n 1` 再对 `<小.json>` 跑上面命令。  
   **导出 Markdown（全员/任意 scored JSON）**：`python -m org_contributor_pipeline.evaluation_run_to_markdown -i <*-scored.json>`（默认在同目录生成 `<stem>.md`，可用 `-o` 指定）。
   产出：Agent 跑分时为 `<stem>.fill-scores.log`；**`--stub`** 时写入 `<stem>.stub-scores.patch.json`（纯 patch，可再用 `merge_evaluation_scores -p` 重放）。合并后均为 `<stem>-scored.json`（见 `merge_evaluation_scores.py`）。  
   **Windows**：命令行长度有限，提示词超过 ``--max-cli-prompt-bytes``（默认 6000 UTF-8 字节）时会自动写入 ``<stem>.fill-scores.prompt.txt``，argv 只传短句让 agent **读该文件**；agent 的标准输出用 **重定向写日志文件**（避免管道捕获为空）。填分任务 **不传 ``--mode=ask``**（ask 为只读 Q&A，易拒绝产出 patch JSON）；一般阶段提示仍可用 ``agent -p --mode=ask`` 做解读。

## 你必须遵守的分工

| 层级 | 谁做 | 产出 |
|------|------|------|
| 事实层 | Python 流水线、GitLab API、`git`、静态分析插件 | `CommitEvent`、`PluginResult` 等 JSON 可序列化结构；含 `evidence` 指针（commit、路径、行号） |
| 研判层 | Cursor 里的 AI（+ 人类负责人） | 与组织评估标准（如 v2）对齐的维度说明、N/A/待评、案例正文；**综合 A/B/C/D 仅作草稿，须人工确认** |

## 推荐对话流程（可打断、可迭代）

1. **材料就位**：本仓库跑出的 artifact 路径，或用户粘贴的摘要/表格。  
2. **身份与窗口**：用 `prompts/01_identity_and_scope.md` 核对 mailmap、bot、时间窗、投入比例是否写清。  
3. **事实解读**：用 `prompts/02_metrics_to_narrative.md` 把插件指标翻成「可复述证据链」，标出缺口。  
4. **维度与综合分层**：用 `prompts/03_rubric_alignment.md` 对齐老板口径（B=达标、A=超预期、C=勉强、D=淘汰建议须高门槛）；区分 **维度档** 与 **综合结论**。  
5. **输出形态**：表格 + 每人「超预期 / 待改进 / 岗位匹配」短文 + **案例**（好设计或低级错误均可定位到提交或文件）。

## 禁止

- 无 artifact 或 artifact 明确不足时，编造 blame 比例、提交数或文件路径。  
- 把「未涉及某类代码」直接打成维度 D；应使用 **N/A（工作安排）** 并说明是否计入综合分母。  
- 在对话中单方面宣布「淘汰」；最多写 **「淘汰风险建议」** 并列出须 HR/主管确认的事项。

## 网页展示用 JSON（evaluation_run.v1）

- **主产物**：`python -m org_contributor_pipeline.emit_evaluation_run -i <artifact.json> -o evaluation_run.json`  
  写出 **`schema_version: evaluation_run.v1`**：每人 **`facts`**（统计事实）+ **`mandatory_l2_scores`**（必审 L2 占位，`grade` 等默认可为 `null`，由研判层 Agent/人写入或 PATCH）。  
- **辅助事实包**：`python -m org_contributor_pipeline.export_technical_fundamentals_facts -i <artifact.json> -o facts.json`（`-o` 以 `.json` 结尾即 JSON；`schema_version: technical_fundamentals_facts.v1`）。  
- **全量 vs 增量（产品约定）**  
  - **全量**：新增考核能力、更换插件/提示词世代、或 `pipeline_capability_epoch` 递增时，对同一项目窗口 **先全量打底**（`--run-kind full`，默认）。  
  - **增量**：仅在 **`workflow.derived_next_run_recommendation === "incremental_eligible"`**（必评人证据门槛全为 `sufficient`）且已有上一版 `evaluation_run.json` 时，使用 `--run-kind incremental --baseline-json <上一版路径>`；**事实永远来自当前 artifact**，上一版仅合并 **非空** 的 `grade`/`narrative_zh` 等。  
  - **附上一次的 JSON（给 LLM / 网页对照）**：提供 `--baseline-json` 时，输出里会增加 **`prior_evaluation_run_attachment`**：`embed_mode` 为 `full` 时内嵌 **上一版全文**；`scores` 时只内嵌 **run + rubric + 每人 mandatory_l2_scores**（省体积）。**`--embed-baseline`**：`auto`（默认）在 **incremental 且带 baseline** 时为 `full`，否则为 `none`；也可显式 `--embed-baseline full|scores|none`（全量跑若也要对比上一版，可 `full + baseline-json`）。  
  - **资料不够打分**：若任一人 `evidence_gate` 为 `insufficient` 或 `partial`，本 JSON 内 **`derived_next_run_recommendation` 为 `full`**，且 **`run_kind_effective` 会强制为 `full`**，**不会**应用 baseline 分数继承（避免在弱证据上叠旧档）。  
- **JSON Schema（校验用）**：`org_contributor_pipeline/schemas/evaluation_run.v1.schema.json`

## 按需 clone 与代码范围（轻量）

当 artifact 含 **`meta.repo_catalog`**（由 `enrich_repo_catalog.py` 生成）时：

- **流水线不 clone** 任何仓库；磁盘与权限由 **人 / Agent** 在有权限的工作区完成。  
- Agent 应 **自行判断** 需要读哪些仓、哪些 `sha`：优先用 **`repo_catalog[].recent_shas`** 与 **`commit_events`** 交叉；只 clone **与当前必评人、当前维度相关的最少集合**，默认 `git clone --depth` 宜浅。  
- 若已跑 **`enrich_commit_diffs`**，先读 **`metadata.commit_diff`**；仍不足再 clone 看完整上下文。  
- **禁止** 无指令时克隆整组全部 28 个仓；若用户明确要求全量，须在对话中显式确认。

## Cursor CLI

可用 `agent -p --mode=ask` 从终端跑阶段提示词；详见 **`docs/CURSOR_CLI.md`** 与 **`scripts/run_cursor_stage.ps1`** / **`run_cursor_stage.sh`**。请在 **仓库根** 设置 `--workspace`，以便加载根目录 `AGENTS.md` 与规则。
