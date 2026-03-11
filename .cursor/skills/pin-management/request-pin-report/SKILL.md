---
name: request-pin-report
description: 根据 PIN 工单生成「Request PIN Report」ADF JSON。先一次性确定全部 PIN ID（用户指定或 latest N/my-requests 列表），再调用 Python tool 并发使用 LLM 分析并产出合并后的 JSON 文档。用户说「生成 PIN 报告」「Request PIN Report」「按 PIN 生成 Confluence 报告」时使用。
---

# Request PIN Report（使用 Python Tool 生成 JSON）

## Purpose

本技能只负责：
- 统一确定要处理的 PIN ID 列表（一次性拿全）
- 调用 Python tool 生成 ADF Body JSON
- 将 JSON 交给 create-page 技能发布到 Confluence

JSON 生成逻辑（含 LLM 并发分析）统一在 `scripts/request_pin_report_json.py` 中实现，Skill 不再手写逐条生成逻辑。

## Input

- 用户明确给出 PIN ID（如 `PIN-2677`、`PIN-2677 PIN-2680`）时：只处理这些 PIN。
- 用户说「最新 N 条」时：取 N 条未处理 PIN。
- 由 my-requests 触发且未特别指定时：默认处理当前列表的全部 PIN。

## Workflow

1. 一次性确定 PIN ID 列表
- 若用户给了 PIN ID：直接整理为列表。
- 若用户给了「最新 N 条」：后续 tool 用 `--latest N` 获取。
- 若来自 my-requests 列表：把列表 key 组装为 `--pin-ids` 参数传给 tool。

2. 调用 JSON 生成 tool（唯一核心步骤）
- 在仓库根目录执行：

```bash
python scripts/request_pin_report_json.py --pin-ids "PIN-2677,PIN-2680" --output /tmp/pin_report_adf.json
```

- 或（最新 N 条）：

```bash
python scripts/request_pin_report_json.py --latest 5 --output /tmp/pin_report_adf.json
```

3. 发布到 Confluence
- 按 `skills/confluence-management/create-page/SKILL.md` 使用 `scripts/confluence_create_page.py`。
- 页面标题：报告生成日 `YYYY-MM-DD Processed`。
- 示例：

```bash
python scripts/confluence_create_page.py --title "2026-03-12 Processed" --body-file /tmp/pin_report_adf.json --body-file-delete-after
```

## Tool Contract

`request_pin_report_json.py` 约定：
- 输入：`--pin-ids` 或 `--latest`
- 处理：
  - 一次 Jira 查询拉取全部 issue（`key in (...)`）
  - 并发调用 LLM 分析每条 description
  - 生成合并后的 ADF JSON 文档
- 输出：
  - `--output` 指定文件时写入文件
  - 未指定 `--output` 时输出到 stdout

## Output Format

输出为 Confluence ADF 根文档：

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {"type": "blockCard", "attrs": {"url": "https://.../browse/PIN-xxxx"}},
    {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "需求要点"}]},
    {"type": "bulletList", "content": [
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "问题：", "marks": [{"type": "strong"}]}, {"type": "text", "text": "..."}]}]},
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "背景：", "marks": [{"type": "strong"}]}, {"type": "text", "text": "..."}]}]},
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "业务影响：", "marks": [{"type": "strong"}]}, {"type": "text", "text": "..."}]}]},
      {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "期望：", "marks": [{"type": "strong"}]}, {"type": "text", "text": "..."}]}]}
    ]}
  ]
}
```

多 PIN 时在各块之间插入 `rule` 分隔。

## Guardrails

- 必须一次性确定 PIN ID 列表，再调用 tool；不要逐条手工生成 JSON。
- Skill 不再维护 Todo-by-ticket 的中间流程。
- 描述归纳必须忠于 Jira 数据，不得杜撰。
- PIN key 必须是 `PIN-<number>`。
- 如果 PIN 超过 10 条，回复里只给数量，不逐条展开。
