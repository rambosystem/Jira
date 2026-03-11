---
name: create-story
description: Create Jira Story tickets for the CP team. Use when user asks to create a Story, story ticket, or user story. Reads structure from issue-structures/story.yaml; uses team, epic-list, sprint-list, label-list.
---

# Create Story

## Purpose

Create Jira **Story** tickets using workspace config and **Story-only** field structure.

## Config (read first)

- `Jira/Assets/Global/profile.yaml`: `me.default_project` when project not specified.
- `Jira/assets/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`, `ticketing.supported_work_types`, `ticketing.defaults.assignee`, `ticketing.defaults.client_id`.
- **Structure**: `Jira/Policy/<project>/issue-structures/story.yaml` — required_fields, optional_fields, field_options, field_defaults.
- `Jira/Policy/<project>/ticket-naming.yaml`: `naming.Story` for title format.
- `Jira/Assets/Global/epic-list.yaml`: `recent_epics` (filter by project key) to resolve Parent.
- `Jira/assets/<project>/sprint-list.yaml`: sprint format and `recent_sprints`.
- `Jira/assets/global/label-list.yaml`: roadmap/cross_team and `recent_labels`.

## MCP 工具链

创建与校验 Story 时用到的 Jira/Atlassian MCP 工具见 **`skills/ticket-management/MCP-tools.md`**（重复检查、用户校验、自定义字段、创建工单、创建后校验）。**直接按 MCP-tools.md 的「快捷参数」表传参即可，无需再读 mcps 下 descriptor。**

## Required inputs

1. Summary (normalized per naming below)
2. Component (from `workspace.ownership.components`)
3. Assignee (required; default from `ticketing.defaults.assignee` if missing)
4. All required fields from `issue-structures/story.yaml`: Story Type, Sprint, Priority, Components, Labels, Client ID, Parent, UX Review Required?
5. Description: optional; if provided use Story template in `skills/ticket-management/ticket-templates/templates.md`.

Apply `field_defaults` from story.yaml when user does not specify (Story Type = Improvement, Client ID = 0000, UX Review Required? = No, UX Review Status = Not Needed).

## Title / summary

Enforce format from `ticket-naming.yaml`: **`[模块] - [平台或范围] - [动作 + 对象]`**.

- 模块: component in brackets e.g. `[SOV]`, `[My Report]`.
- 平台或范围: `All Platforms` or slash e.g. `Amazon/Walmart/Target`.
- 动作 + 对象: formal wording; prefer `<业务主体> + <动作> + <对象>`; avoid colloquial phrases.
- If user summary does not match, rewrite to this format, show in Ticket Name List, get confirmation before create.

## Workflow

1. **Project**: From user or `me.default_project`. Ensure Story is in `ticketing.supported_work_types`.
2. **Validate**: Component in ownership; assignee in team or external (verify external via Jira/Confluence user lookup **`jira_get_user_profile`** or Confluence user search; if new, add to `team.external_members`). All Story required fields present; validate against field_options.
3. **Sprint**: Required unless assignee in `team.external_members`. Format `YYQn-Sprintm-Defenders`. Prefer `recent_sprints`.
4. **Parent**: Resolve from `epic-list.yaml` (recent_epics by project; match component/quarter). If no match, ask user.
5. **Labels**: Roadmap `roadmap_YYqN`; add `cross-team` if cross-team work. Prefer `recent_labels`.
6. **Duplicate check** (**`jira_search_issues`**): Search same project + Story + summary; if exists, ask reuse or new.
7. **Ticket Name List**: List summary(ies) to create; ask explicit confirmation.
8. **Assignee**: Prefer email → name → account_id for Jira. Persist external as name, account_id, email.
9. **Custom fields** (**`jira_search_fields`**): Resolve Parent, Client ID, UX fields; set via `additional_fields`. Parent as string: `"parent": "CP-123"`.
10. **Create** (**`jira_create_issue`**): Project, type Story, Summary, Assignee, Component, optional Description.
11. **Post-create** (**`jira_get_issue`** / **`jira_get_issue_by_key`**): Verify Summary, Type, Assignee, Priority, Components, Labels, Parent, Sprint; report PASS/FAIL.

## Guardrails

- Only components in `workspace.ownership.components`. Validate assignee; verify external before use.
- Pre-create Ticket Name List and explicit confirmation. No raw summary; always normalized title.
- Follow `issue-structures/story.yaml`; do not invent fields. Default Priority Medium, Client ID 0000.
- Use MCP-tools.md 快捷参数调用 MCP；无需读 schema。Duplicate check before create; post-create validation required.

## Output

Before create: **Ticket Name List**, **Confirmation Needed: Yes**.

After create: **Issue**, **URL**, **Type: Story**, **Component**, **Assignee**, **Project**, **Validation**, **Validation Details**.
