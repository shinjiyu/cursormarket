# evaluation_run 评审报告（Markdown）

- **来源**：`D:\tools\cursorLogViewer\org_contributor_pipeline\artifacts\generated\evaluation_run-demo-scoped-scored.json`
- **schema_version**：evaluation_run.v1

## 运行元数据

| 字段 | 值 |
|------|-----|
| run_id | dad43046-2012-42f3-9d44-a015abc727c3 |
| created_at | 2026-05-13T14:27:28Z |
| run_kind_effective | full |
| artifact_path | D:\tools\cursorLogViewer\org_contributor_pipeline\artifacts\generated\gitlab_group_artifact_scoped.json |
| artifact_fingerprint | f0ee2a724f5a8620febd5a11 |
| window_start | 2026-03-01T00:00:00Z |
| window_end | 2026-05-13T00:00:00Z |
| gitlab_group | h5_game_sh_tpe |
| ingest.commit_row_count | 2595 |
| scores_merge | {"schema_version": "evaluation_run_scores_patch.v1", "patch_filled_by": "cursor_agent_cli"} |

## workflow 摘要

| 字段 | 值 |
|------|-----|
| evidence_tier | weak |
| derived_next_run_recommendation | full |
| reason_zh | 存在必评人员资料不足以稳定覆盖必审 L2（diff/体量门槛未过）；下次仍须先全量打分。 |

## 必评人员（共 8 人）

## 林耕宇

| 字段 | 值 |
|------|-----|
| person_key | ericlin09.fgrd3@gmail.com |
| game_zh | 赛特2 |
| primary_project_path_prefix | h5_game_sh_tpe/seth2 |
| evidence_gate | sufficient |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 882 |
| insertions | 325373 |
| deletions | 215256 |
| distinct_projects | 13 |
| first_day | 2026-03-02 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 0 |
| fix_like | 0 |
| game_biz | 0 |
| merge_like | 39 |
| observability | 22 |
| quality_gate | 7 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 13 |
| vcs_active_days_summed | 133 |
| vcs_commit_count_summed | 882 |
| vcs_max_lines_single_commit | 81560 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | — | 低 | commit_diff_ok=0，标题多为 init/Merge/l10n，缺少 diff/MR 无法核对算法与边界实现；请补代表性 MR。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | B | 中 | 窗口内持续触及 seth2 多客户端与 extension-tools/common-ui 路径（例 ba0c380… l10n、0a3cf1c… 清理 dev 资源），语言栈深度待静态分析。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 未见迁移/事务/ORM 等标题或路径关键词；材料 N/A，需补后端/存储相关 MR。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 中 | 工程化目录与多仓协作可见：common-ui 与多项目 init/维护类提交并存（例 0a3cf1c…）。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | B | 中 | 13 个 delivery_slices、跨 game_client/common/art/extension_tools 路径分层与多仓活动明确。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 中 | 可维护性线索：ba0c380…「l10n 預設繁中」、0a3cf1c…「移除 dev 相關代碼與資源」。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | B | 中 | commit_title_signals quality_gate=7；缺 CI 结果链接，结论为弱代理。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | — | 低 | cicd 标题命中=0；无 pipeline/release 材料可核对。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | B | 中 | observability 标题命中=22；需工单/MR 佐证线上排障闭环。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | B | 高 | 882 commits、13 slices、133 活动日累加，web_url 样本完整，Git 代理轨迹清晰。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | B | 中 | path_taxonomy 显示 client/common/art/tools 多桶分布；重大架构结论仍待设计文档。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 标题/路径未出现限流/容灾/多活等关键词；材料不足。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无 MQ/缓存/消费顺序类提交标题或配置路径线索。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态机/补偿/成本类可见标题；无法从元数据推断。 | cursor_agent_cli |

## 包峰華

| 字段 | 值 |
|------|-----|
| person_key | dpunity920000@gmail.com |
| game_zh | 大闹东海 |
| primary_project_path_prefix | h5_game_sh_tpe/da-nao-dong-hai |
| evidence_gate | sufficient |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 189 |
| insertions | 10484812 |
| deletions | 1856839 |
| distinct_projects | 21 |
| first_day | 2026-03-13 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 1 |
| fix_like | 1 |
| game_biz | 0 |
| merge_like | 8 |
| observability | 0 |
| quality_gate | 1 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 21 |
| vcs_active_days_summed | 67 |
| vcs_commit_count_summed | 189 |
| vcs_max_lines_single_commit | 2672013 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | — | 低 | 无 commit_diff；大体量 init project 为主，无法判断算法/复杂度实现细节。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | B | 中 | 跨多游戏仓客户端与 common 美术仓持续 init/集成（例 a075c97…、365fc9d…、99735e0…）。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 窗口内未见存储/迁移类标题；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 低 | 大量工程 init 与多仓目录触达，缺具体构建/MR 细节。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | B | 中 | 21 个 slices、跨 da-nao-dong-hai/ma-jiang-hu-le/seth2/extension-tools/common。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 低 | 样本以 init project 与 merge 类提交为主，可维护性证据偏薄。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | C | 低 | quality_gate 命中=1；需补测试/lint/评审记录。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | C | 低 | cicd 命中=1；需补 pipeline 链接与发布记录。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | — | 低 | observability 命中=0；无日志/指标/trace 标题线索。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | B | 高 | 189 commits、21 slices、67 活动日，交付 footprint 明确。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | B | 中 | 跨多项目路径与 path_taxonomy 桶分布可交叉；架构结论待文档。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 无规模/可用性关键词标题。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无中间件/MQ/缓存样本。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态/成本类标题证据。 | cursor_agent_cli |

## 李紳旭

| 字段 | 值 |
|------|-----|
| person_key | psunnysunq@gmail.com |
| game_zh | 喵財進寶 |
| primary_project_path_prefix | h5_game_sh_tpe/miao-cai-jin-bao |
| evidence_gate | sufficient |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 49 |
| insertions | 251783 |
| deletions | 28279 |
| distinct_projects | 3 |
| first_day | 2026-04-22 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 0 |
| fix_like | 0 |
| game_biz | 0 |
| merge_like | 4 |
| observability | 0 |
| quality_gate | 0 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 3 |
| vcs_active_days_summed | 18 |
| vcs_commit_count_summed | 49 |
| vcs_max_lines_single_commit | 40129 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | — | 低 | 无 diff；主仓为 artwork，标题偏动效/美术，无法论证算法实现。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | — | 低 | 材料以美术资源为主，运行栈深度需客户端/MR 补证。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 未见持久化相关标题；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 中 | 美术管线提交密集（例 533ae61… 连线框、aa8f03b… 动效），可见设计资产迭代。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | C | 中 | 3 slices，主聚焦 miao-cai-jin-bao artwork，模块化证据有限。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 低 | bd1b325… Merge 与多笔动效标题显示持续迭代。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | — | 低 | quality_gate=0；无测试/lint 代理命中。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | — | 低 | cicd=0；无 CI/CD 标题线索。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | — | 低 | observability=0。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | B | 中 | 49 commits、18 活动日、3 slices；样本少于工程岗但轨迹清楚。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | C | 低 | 兼触 lei-shen-zhi-chui artwork；跨仓范围有限。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 无规模/可用性关键词。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无中间件样本。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态/成本类证据。 | cursor_agent_cli |

## 蕭志文

| 字段 | 值 |
|------|-----|
| person_key | fg000406@fingergame.com.tw |
| game_zh | 麻將胡了 |
| primary_project_path_prefix | h5_game_sh_tpe/ma-jiang-hu-le |
| evidence_gate | sufficient |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 457 |
| insertions | 501945 |
| deletions | 1192727 |
| distinct_projects | 5 |
| first_day | 2026-03-02 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 1 |
| fix_like | 2 |
| game_biz | 0 |
| merge_like | 19 |
| observability | 4 |
| quality_gate | 2 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 5 |
| vcs_active_days_summed | 87 |
| vcs_commit_count_summed | 457 |
| vcs_max_lines_single_commit | 733299 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | — | 低 | 无 commit_diff；大体量资源增删与 UI 变更无法反推算法细节。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | B | 中 | extension-tools/common-ui/project-l 与 ma-jiang-hu-le 客户端/artwork 并行（例 c3b59c4…、a46e51d…）。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 未见存储层标题；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 中 | Common UI 新页面与旧 prefab 清理（c3b59c4… BuyFeature、d17ea1c… 刪除舊 prefab）。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | B | 中 | 5 slices，跨 common-ui 与主游戏 client/artwork。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 中 | 9caea94… 刪除暫代資源、be7166e… 新增暫代資源，显示资源周转维护。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | B | 低 | quality_gate=2；仍缺 CI 详细结果。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | C | 低 | cicd=1；证据弱。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | C | 低 | observability=4；无工单链。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | B | 高 | 457 commits、5 slices、87 活动日，footprint 强。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | B | 中 | path_taxonomy：client/common/art 组合；架构结论待 MR。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 无规模/可用性关键词。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无中间件样本。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态/成本类标题。 | cursor_agent_cli |

## 李育瑋

| 字段 | 值 |
|------|-----|
| person_key | pd36579@gmail.com |
| game_zh | 仙境傳說 |
| primary_project_path_prefix | h5_game_sh_tpe/xian-jing-chuan-shuo |
| evidence_gate | sufficient |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 185 |
| insertions | 527062 |
| deletions | 254304 |
| distinct_projects | 10 |
| first_day | 2026-03-03 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 0 |
| fix_like | 0 |
| game_biz | 0 |
| merge_like | 8 |
| observability | 0 |
| quality_gate | 0 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 10 |
| vcs_active_days_summed | 76 |
| vcs_commit_count_summed | 185 |
| vcs_max_lines_single_commit | 83264 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | — | 低 | 无 diff；样本偏美術/UI 資源大块变更，复杂度不可见。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | — | 低 | 语言深度需代码/MR；当前多为资源与共用 UI 路径标题。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 无存储相关标题；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 中 | 392c6cb…「H線共用UI直橫版」、ffae61d… 美術資源上傳，可见 UI/資產整合。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | B | 低 | 10 slices，跨 extension-tools/common 与 seth2 artwork。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 低 | fe0038a… Merge 与 e9341e2… 美術更新显示持续维护。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | — | 低 | quality_gate=0。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | — | 低 | cicd=0。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | — | 低 | observability=0。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | B | 中 | 185 commits、76 活动日、10 slices。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | B | 低 | 多仓 artwork/common-ui；架构深度待文档。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 无规模/可用性关键词。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无中间件样本。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态/成本证据。 | cursor_agent_cli |

## 蔡政廷

| 字段 | 值 |
|------|-----|
| person_key | jackal0807@hotmail.com |
| game_zh | 雷神之錘 |
| primary_project_path_prefix | h5_game_sh_tpe/lei-shen-zhi-chui |
| evidence_gate | sufficient |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 55 |
| insertions | 59228 |
| deletions | 33520 |
| distinct_projects | 5 |
| first_day | 2026-04-07 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 13 |
| fix_like | 0 |
| game_biz | 0 |
| merge_like | 1 |
| observability | 0 |
| quality_gate | 1 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 5 |
| vcs_active_days_summed | 18 |
| vcs_commit_count_summed | 55 |
| vcs_max_lines_single_commit | 25371 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | — | 低 | 无 diff；标题以語系/規則頁/prefab 为主，算法面不可见。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | B | 中 | proj-l-client 与 artwork prefab 并行（例 52e5115… 語系、ed98304… prefab）。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 无存储层标题；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 中 | dev_tool/Symbol/maingame prefab 增量与規則頁更新显示工具化配置触及。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | B | 低 | 5 slices，client+artwork 分层可见。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 低 | 多笔「新增/更新」类 prefab 与規則頁文件维护。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | C | 低 | quality_gate=1；证据弱。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | B | 中 | cicd 标题命中=13；仍需 pipeline 链接核实非标题噪声。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | — | 低 | observability=0。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | B | 中 | 55 commits、18 活动日、5 slices；窗口相对短但清晰。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | B | 低 | path_taxonomy 以 game_client 为主；架构结论待 MR。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 无规模/可用性关键词。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无中间件样本。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态/成本证据。 | cursor_agent_cli |

## 于振宇

| 字段 | 值 |
|------|-----|
| person_key | 1806153872@qq.com |
| game_zh | （跨仓 / 工具） |
| evidence_gate | partial |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 11 |
| insertions | 8860 |
| deletions | 417 |
| distinct_projects | 3 |
| first_day | 2026-04-30 |
| last_day | 2026-05-12 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 0 |
| fix_like | 3 |
| game_biz | 0 |
| merge_like | 0 |
| observability | 4 |
| quality_gate | 1 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 3 |
| vcs_active_days_summed | 5 |
| vcs_commit_count_summed | 11 |
| vcs_max_lines_single_commit | 4339 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | B | 低 | genbot CLI/代码生成与模块拆分（例 e2d6551… MVP、666bae3… 拆分）提示实现面复杂度，但无 diff 不敢升档。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | B | 中 | TypeScript/Cocos editor 集成与 Inspector UI（78488834…）路径在 extension-tools/genbot。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 无存储相关提交；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | B | 中 | 工具链+文档目录（8070b3d… docs）+ 多 feat 迭代，工程化底座可见。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | B | 中 | 666bae3… 拆分 gen.ts/view.ts、default-rule 调整显示模块化取向。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | B | 中 | eaa3152… default-rule 与多版本 feat 文档并进。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | C | 低 | quality_gate=1；需补测试与 CI。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | — | 低 | cicd=0；无 pipeline 材料。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | C | 低 | observability=4 + fix_like=3，缺线上闭环材料。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | C | 低 | evidence_gate=partial：11 commits、5 活动日，Git 代理样本偏少。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | B | 低 | extension_tools 桶占主导；系统边界结论仍待设计说明。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | — | 低 | 无规模/可用性关键词。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | — | 低 | 无中间件样本。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | — | 低 | 无状态/成本证据。 | cursor_agent_cli |

## 秦超

| 字段 | 值 |
|------|-----|
| person_key | 932493926@qq.com |
| game_zh | （公共 / 协议） |
| evidence_gate | partial |

### 事实摘要（facts）

| 指标 | 值 |
|------|-----|
| commit_rows | 2 |
| insertions | 68 |
| deletions | 6 |
| distinct_projects | 1 |
| first_day | 2026-05-07 |
| last_day | 2026-05-07 |

| commit_diff | 值 |
|-------------|-----|
| commit_diff_ok | 0 |

| title_signal_commit_hits | 值 |
|----------------------------|-----|
| cicd | 0 |
| fix_like | 0 |
| game_biz | 0 |
| merge_like | 0 |
| observability | 2 |
| quality_gate | 0 |

| delivery_vcs_summed | 值 |
|---------------------|-----|
| delivery_slices | 1 |
| vcs_active_days_summed | 1 |
| vcs_commit_count_summed | 2 |
| vcs_max_lines_single_commit | 61 |

### 必审 L2

| L1 | L2 | grade | confidence | narrative_zh | filled_by |
|----|-----|-------|------------|--------------|-----------|
| 基础技术能力 | 数据结构、算法与复杂度 | 待评 | 低 | 窗口仅 2 笔提交且 commit_diff_ok=0，无法评估算法与数据结构实现。 | cursor_agent_cli |
| 基础技术能力 | 语言深度与运行栈 | C | 低 | 77017cf6…/358212b4… 位于 project-l-common，偏协议日志小改动；深度待更多样本。 | cursor_agent_cli |
| 基础技术能力 | 数据与持久化 | — | 低 | 无存储迁移类证据；N/A（材料）。 | cursor_agent_cli |
| 基础技术能力 | 设计表达与工程化底座 | — | 低 | 无设计/构建类标题样本。 | cursor_agent_cli |
| 工程能力 | 结构、模块化与解耦 | 待评 | 低 | 提交过少，难言模块化结构与解耦取舍。 | cursor_agent_cli |
| 工程能力 | 可维护性与演进 | C | 低 | 两笔皆为协议日志增补/可开关调试，演进面证据有限。 | cursor_agent_cli |
| 工程能力 | 规范与质量门禁 | 待评 | 低 | 无 quality_gate 命中样本。 | cursor_agent_cli |
| 工程能力 | CI/CD 与发布 | 待评 | 低 | 无 CI/CD 触碰记录。 | cursor_agent_cli |
| 工程能力 | 可观测性与排障 | B | 低 | 标题明确「协议打印日志/调试日志，可开关」，observability 命中=2。 | cursor_agent_cli |
| 工程能力 | 版本库活动与可追溯（Git 代理） | C | 低 | 2 commits、1 日、1 slice；footprint 极薄。 | cursor_agent_cli |
| 系统设计能力 | 架构与边界 | 待评 | 低 | 仅 common 小改，难言架构边界。 | cursor_agent_cli |
| 系统设计能力 | 规模、并发与可用性 | 待评 | 低 | 无规模/可用性材料。 | cursor_agent_cli |
| 系统设计能力 | 数据路径与中间件 | 待评 | 低 | 无中间件材料。 | cursor_agent_cli |
| 系统设计能力 | 状态、一致性与成本 | 待评 | 低 | 无状态/成本材料。 | cursor_agent_cli |

---

*权威数据以 JSON 为准；本文件为二次整理。*
