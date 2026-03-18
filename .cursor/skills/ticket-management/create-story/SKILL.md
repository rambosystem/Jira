---
name: create-story
description: Create Jira Story tickets for the CP team. Assemble a structured issue plan first, then create through MCP after confirmation. Read rules from config/policy/<project>/ticket-schema.json and naming from ticket-naming.yaml.
---

# Create Story

## Purpose

Create Jira Story tickets using workspace config and the project ticket schema.

## Config

- `Jira/config/assets/global/profile.yaml`: `me.default_project`
- `Jira/config/assets/project/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`
- `Jira/config/policy/<project>/ticket-schema.json`: `supported_work_types`, `defaults`, `issue_types.Story`
- `Jira/config/policy/<project>/ticket-naming.yaml`: `naming.Story`
- `Jira/config/assets/global/epic-list.yaml`: parent resolution
- `Jira/config/assets/project/<project>/sprint-list.yaml`: sprint naming
- `Jira/config/assets/global/label-list.yaml`: roadmap and labels

## MCP Tools

- `jira_create_issue`
- `jira_add_issues_to_sprint` when user specifies Sprint（创建后立即加入）
- `jira_get_agile_boards`、`jira_get_sprints_from_board` 用于按 sprint 名称解析出 sprint_id
- `jira_create_issue_link` when PIN links are explicitly provided
- `jira_get_issue` only for post-check when needed

## Required schema + defaults

- Build from `ticket-schema.json` only.
- Use `issue_types.Story.required_fields` + `field_defaults` + user input.
- Use `defaults.assignee` when user does not provide assignee. **Assignee 传参**：传给 Jira 的 assignee 一律使用**邮箱**（`defaults.assignee.email`），因 create 时 account_id 可能不生效；若 schema 无 email 则从 `team.yaml` 按 name 解析出 email。
- Add optional fields only when user provided them or Jira create requires them.

## Required Payload 模块（直接替换）

调用 `jira_create_issue` 时：传 `project_key`、`summary`、`issue_type`（Story）、`assignee`（**使用邮箱**，如 `defaults.assignee.email`）、`components`；其余字段放入 `additional_fields`（JSON 字符串）。**MCP 要求**：`additional_fields` 中的 `parent` 必须为 **字符串**（如 `"parent": "CP-46176"`），不可用对象 `{"key": "..."}`，否则会报错 "expected 'key' property to be a string"。

`additional_fields` 示例（占位符替换为实际值）：

```json
{
  "parent": "<PARENT_KEY>",
  "priority": { "name": "<PRIORITY>" },
  "customfield_10043": ["<CLIENT_ID>"],
  "customfield_10085": { "value": "<STORY_TYPE>" },
  "customfield_13319": { "value": "<UX_REVIEW_REQUIRED>" },
  "customfield_13320": { "value": "<UX_REVIEW_STATUS>" }
}
```

- **占位符**: `<PARENT_KEY>`=**必填**，Epic 或上级 Issue key（字符串）；`<PRIORITY>`=schema field_options.Priority，`<CLIENT_ID>`=默认 "0000"，`<STORY_TYPE>`=默认 "Improvement"，`<UX_REVIEW_REQUIRED>`=默认 "No"，`<UX_REVIEW_STATUS>`=默认 "Not Needed"。
- **可选**: 有描述时在调用中传 `description` 参数。

## Preferred Execution

- Prefer MCP for Jira create and link actions.

## Required Inputs

1. Summary
2. **Parent** (Epic 或上级 Issue key，强制)
3. Component
4. Assignee
5. Story-specific required fields from `ticket-schema.json` `issue_types.Story`
6. Optional description
7. Optional **Sprint**（用户指定则创建后一次性加入该 Sprint，使用 `sprint-list.yaml` 的命名，如 `26Q1-Sprint6-Defenders` 或简写 Sprint 6）
8. Optional `--link-pin`

Default assignee: use `defaults.assignee.email` from `ticket-schema.json` when passing to Jira (create/update). If schema has no email, resolve from `team.yaml` by `defaults.assignee.name`.
Default field values should come from `ticket-schema.json` `issue_types.Story.field_defaults`.

## Rules

- **Story 强制 Parent**：创建前必须确定 Parent（Epic 或上级 Issue）；无 Parent 时先推荐/解析 Epic，再创建。
- Validate Story is listed in `ticket-schema.json` `supported_work_types`.
- Follow `ticket-schema.json` `issue_types.Story.required_fields`, `optional_fields`, `field_options`, and `field_defaults`.
- Do not invent fields outside schema and Jira field mapping.
- Use naming from `ticket-naming.yaml`.
- Build the draft quickly from required fields plus applicable defaults.
- Do not include optional fields unless the user provided them or they are needed to review/create the issue.
- Do not run duplicate checks or show duplicate references.

## Workflow

1. Collect inputs（含可选的 Sprint）。
2. Normalize title and assemble the required schema with defaults.
3. Show a concise draft before any create action. Do not ask extra questions unless required information is missing or the user asks to adjust it.
4. **解析并确定 Parent（强制）**：按模块/季度推荐 Epic 或使用用户指定的 Parent；无合适 Epic 时提示并请用户先创建 Epic 或提供 Parent key。
5. **若用户指定 Sprint**：从 `sprint-list.yaml` 解析 sprint 全名（如「Sprint 6」→ 当前季度的 `26Q1-Sprint6-Defenders`），写入 draft 便于确认。
6. Review key fields and confirmed Parent (and Sprint if any) before create.
7. Wait for user confirmation or correction.
8. Create once from the confirmed plan through MCP（assignee 传邮箱，如 `defaults.assignee.email`）。
9. **若用户指定了 Sprint**：用 `jira_get_agile_boards(project_key)` 取项目 board_id，再用 `jira_get_sprints_from_board(board_id)` 按名称匹配得到 sprint_id，然后 `jira_add_issues_to_sprint(sprint_id, 新建的 issue_key)`，实现创建与入 Sprint 一次性完成。
10. **若创建后 assignee 未生效**（接口返回 Unassigned）：用 `jira_update_issue(issue_key, fields: {"assignee": "<email 或 name>"})` 再设一次。
11. If PIN keys are provided, create `Relates` links.
12. Post-check key fields.

## Output

- Before create: Concise Draft, Parent（必填）, Sprint（若指定）, Confirmation Needed
- After create: Issue, URL, Type, Component, Assignee, Project, Sprint（若已加入）, Validation, Validation Details
