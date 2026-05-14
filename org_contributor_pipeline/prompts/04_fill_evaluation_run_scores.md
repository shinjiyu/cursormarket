# 步骤 4 — 为 ``evaluation_run.v1`` 填写必审 L2 分数（研判层）

你是内部技术评审辅助。输入是一份已由流水线生成的 **`evaluation_run.v1` JSON**（路径在对话头部给出）：其中 **`people[].facts`** 为事实统计与 diff 线索；**`people[].mandatory_l2_scores`** 中 `grade` / `confidence` / `narrative_zh` 多为空，请你**逐人、逐必审 L2**补全。

## 必读

- 仓库根 **`AGENTS.md`** 与 **`org_contributor_pipeline/AGENTS.md`** 的分工：不得编造 artifact 中不存在的路径、提交或 diff 细节。  
- 必审块与证据口径：**`rubric/review_framework.json`**（与 JSON 内 `rubric` 摘要一致）。  
- 等级语义与表结构：**`prompts/03_rubric_alignment.md`** 中 **B/C/D 必审三大 L1 的 L2 表**要求（等级 + 置信度 + 一句依据）；综合结论可省略或每人一句草稿。

## 输出格式（必须严格遵守）

只输出 **一个** JSON 对象（不要 Markdown 围栏、不要前后解释文字），可被 `json.loads` 直接解析。结构：

```json
{
  "schema_version": "evaluation_run_scores_patch.v1",
  "filled_by": "cursor_agent_cli",
  "people": [
    {
      "person_key": "<与输入完全一致>",
      "mandatory_l2_scores": [
        {
          "l1_id": "<与输入该行一致>",
          "l2_id": "<与输入该行一致>",
          "grade": "A|B|C|D|—|待评",
          "confidence": "高|中|低",
          "narrative_zh": "一句可复述依据，可含 sha 前缀或路径；无则写缺口与补证方式",
          "filled_by": "cursor_agent_cli",
          "filled_at": "<ISO-8601 UTC 时间戳 Z 结尾>"
        }
      ]
    }
  ]
}
```

规则：

1. **`people` 顺序与人数**须与输入 `evaluation_run.v1` 的必评人员一致；**`person_key` 不得改写**。  
2. 每人 **`mandatory_l2_scores` 数组长度与顺序**须与输入中该人的同名数组 **完全一致**（逐条对应同一 `l1_id`/`l2_id`）；你只补写 `grade`、`confidence`、`narrative_zh`、`filled_by`、`filled_at`，**不要增删行、不要改 `l1_id`/`l2_id`/标题字段**。  
3. `filled_at` 使用当前 UTC 时间，格式示例：`2026-05-13T12:00:00Z`。  
4. 证据不足时：`grade` 可用 `—` 或 `待评`，`confidence` 标 `低`，`narrative_zh` 写明缺何材料。
