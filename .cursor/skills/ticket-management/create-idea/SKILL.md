---
name: create-idea
description: Create PACID Idea tickets for the Middle Platform team. Use when user asks to create an Idea, PACID Idea, or "在 PACID 建一条 Idea". Follows policy/PACID/issue-structures/idea-middle-platform.yaml (required_by_team, description_template, field_defaults). Uses MCP jira_create_issue with project PACID, issue_type Idea, and custom fields via additional_fields.
---

# Create Idea (PACID)

## Purpose

Create **PACID** project **Idea** tickets for the **Middle Platform** team, using the team’s required fields and description template.

## Config (read first)

- **Structure**: `policy/PACID/issue-structures/idea-middle-platform.yaml` — `required_by_team`, `description_template`, `field_defaults`.
- **Profile**: `assets/global/profile.yaml` — `me.account_id`, `me.name`, `me.email` for default assignee.
- **Createmeta** (optional): `docs/pacid-createmeta.json` for full field keys/options.

## Required inputs (Middle Platform)

**只填** `idea-middle-platform.yaml` 中 `required_by_team` 列出的字段，其余不填。

1. **Summary** — 标题，一句话概括 Idea。
2. **Description** — 使用下方 description_template；若用户只给要点，代为展开成模板结构。
3. **Assignee** — 负责人；未指定时用 `profile.me.account_id` 或 `me.email`。
4. **Teams** — 固定 `Ads`（Middle Platform 约定）。
5. **Client Segment** — 固定 `Pacvue`。
6. **Release Status** — 默认 `Discovery`；用户可指定 Discovery / Development / Alpha / Beta / GA / Product Backlog。

## Description template

Use the template from `idea-middle-platform.yaml`:

```markdown
**What we are building?**
（我们在做什么 / 功能概述）

**Why are we building it?**
（为什么做 / 背景与目标）

**💡 Customer Problem**
（用户/客户面临的问题）

**🔥 Customer Benefit**
（带来的价值与收益）

**🎯 Expected Business Impact**
（预期业务影响 / 成功指标）
```

若用户只提供简短说明，将内容填入对应小节，其余小节用占位或“待补充”。

## Execution (MCP)

1. **Read** `policy/PACID/issue-structures/idea-middle-platform.yaml` 得到 `required_by_team`、`field_defaults`、`description_template`。
2. **Collect**: summary, description（或按模板生成）, assignee（默认 profile.me）, Release Status（默认 Discovery）。
3. **Build additional_fields**（JSON 字符串）**仅包含必填自定义字段**：
   - `customfield_10278` (Teams): `[{"value": "Ads"}]` 或等价结构（依 Jira API 要求）。
   - `customfield_10508` (Client Segment): `[{"value": "Pacvue"}]`。
   - `customfield_10726` (Release Status): `{"value": "Discovery"}` 或用户指定值。
4. **Call** MCP `user-mcp-atlassian` · **`jira_create_issue`**:
   - `project_key`: **PACID**
   - `issue_type`: **Idea**
   - `summary`: 用户确认的标题
   - `description`: 按模板填好的 ADF 或 Markdown（若 API 接受 Markdown 则直接传）
   - `assignee`: 用户指定或 profile 的 email/accountId
   - `additional_fields`: 仅上述三个必填自定义字段（Teams、Client Segment、Release Status）。注意 Jira Cloud 对 option/array 的格式要求，可参考 createmeta。
5. **Output**: 返回 created issue key、URL、Summary、Assignee、Release Status、以及已填的自定义字段摘要。

## Field keys（仅必填，创建时只传这三项自定义字段）

| 显示名         | Key               | 说明 |
|----------------|-------------------|------|
| Teams          | customfield_10278  | array, 固定 Ads |
| Client Segment | customfield_10508  | array, 固定 Pacvue |
| Release Status | customfield_10726  | option: Discovery, Development, Alpha, Beta, GA, Product Backlog |

具体 option/array 的 id/value 以 `docs/pacid-createmeta.json` 或 Jira API 返回为准。

## Guardrails

- 项目固定为 **PACID**，issue_type 固定为 **Idea**。
- **只传** `idea-middle-platform.yaml` 中 `required_by_team` 的字段；非必填字段一律不传。
- 不杜撰字段 key。
- Assignee 未指定时用 profile 的 `me.account_id` 或 `me.email`。
- Description 必须包含 template 中五段结构（可部分待补充），不要只写一句纯文本。

## Output

- **Before create**: 列出 Summary、Assignee、Release Status、Description 是否按模板，请用户确认。
- **After create**: **Issue key**、**URL**、**Summary**、**Assignee**、**Release Status**、**Client Segment**、**Teams**。
