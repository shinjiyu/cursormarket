# Prompts（在 Cursor 对话中使用）

将下列 Markdown **整段复制进对话**，或作为 `@文件` 引用，让 Agent 按阶段执行。**不要**期望仅运行 Python 就得到最终人事结论。

| 文件 | 阶段 |
|------|------|
| `01_identity_and_scope.md` | 身份归一、时间窗、投入比例、岗位范围 |
| `02_metrics_to_narrative.md` | 指标 → 证据链叙述，标缺口 |
| `03_rubric_alignment.md` | 对齐 v2 类量表：维度档 vs 综合结论、N/A、待评 |

可在同一会话中多次切换阶段；若 artifact 更新，从阶段 2 重跑即可。
