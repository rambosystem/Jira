---
name: create-technical-story
description: Create Jira Technical Story tickets for the CP team. Use when user asks to create a Technical Story or tech story. Reads structure from issue-structures/technical-story.yaml; uses team, epic-list, sprint-list, label-list.
---

# Create Technical Story

## Purpose

Create Jira **Technical Story** tickets using workspace config and **Technical Story-only** field structure.

## Config (read first)

- `Jira/Assets/Global/profile.yaml`: `me.default_project` when project not specified.
- `Jira/assets/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`, `ticketing.supported_work_types`, `ticketing.defaults.assignee`, `ticketing.defaults.client_id`.
- **Structure**: `Jira/Policy/<project>/issue-structures/technical-story.yaml` — required_fields, optional_fields, field_options, field_defaults.
- `Jira/Policy/<project>/ticket-naming.yaml`: `naming.Technical Story` (inherits Story format).
- `Jira/Assets/Global/epic-list.yaml`: `recent_epics` (filter by project key) to resolve Parent.
- `Jira/assets/<project>/sprint-list.yaml`: sprint format and `recent_sprints`.
- `Jira/assets/global/label-list.yaml`: roadmap/cross_team and `recent_labels`.

## MCP 工具链

创建与校验 Technical Story 时用到的 Jira/Atlassian MCP 工具见 **`skills/ticket-management/MCP-tools.md`**（重复检查、用户校验、自定义字段、创建工单、创建后校验）。**直接按 MCP-tools.md 的「快捷参数」表传参即可，无需再读 mcps 下 descriptor。**

## Required inputs

1. Summary (normalized per naming below)
2. Component (from `workspace.ownership.components`)
3. Assignee (required; default from `ticketing.defaults.assignee` if missing)
4. All required fields from `issue-structures/technical-story.yaml`: Technical Story Type, Sprint, Priority, Components, Labels, Client ID, Parent.
5. Description: optional; if provided use Story template in `skills/ticket-management/ticket-templates/templates.md`.

Apply `field_defaults` from technical-story.yaml (Client ID = 0000) when user does not specify.

## Title / summary

Same as Story (from `ticket-naming.yaml`): **`[模块] - [平台或范围] - [动作 + 对象]`**.

- 模块: component in brackets. 平台或范围: `All Platforms` or slash. 动作 + 对象: formal wording; prefer domain-subject style; avoid colloquial.
- If user summary does not match, rewrite, show in Ticket Name List, get confirmation before create.

## Workflow

1. **Project**: From user or `me.default_project`. Ensure Technical Story is in `ticketing.supported_work_types`.
2. **Validate**: Component in ownership; assignee in team or external (verify via **`jira_get_user_profile`** or Confluence user search; add to `team.external_members` if new). All Technical Story required fields present; validate against field_options.
3. **Sprint**: Required unless assignee in `team.external_members`. Format `YYQn-Sprintm-Defenders`. Prefer `recent_sprints`.
4. **Parent**: Resolve from `epic-list.yaml` (recent_epics by project; match component/quarter). If no match, ask user.
5. **Labels**: Roadmap `roadmap_YYqN`; add `cross-team` if needed. Prefer `recent_labels`.
6. **Duplicate check** (**`jira_search_issues`**): Search same project + Technical Story + summary; if exists, ask reuse or new.
7. **Ticket Name List**: List summary(ies); ask explicit confirmation.
8. **Assignee**: Prefer email → name → account_id. Persist external as name, account_id, email.
9. **Custom fields** (**`jira_search_fields`**): Resolve Parent, Client ID; set via `additional_fields`. Parent as string: `"parent": "CP-123"`.
10. **Create** (**`jira_create_issue`**): Project, type Technical Story, Summary, Assignee, Component, optional Description.
11. **Post-create** (**`jira_get_issue`** / **`jira_get_issue_by_key`**): Verify Summary, Type, Assignee, Priority, Components, Labels, Parent, Sprint; report PASS/FAIL.

## Guardrails

- Only components in `workspace.ownership.components`. Validate and verify external assignee.
- Pre-create Ticket Name List and explicit confirmation. Always normalized title.
- Follow `issue-structures/technical-story.yaml`; do not invent fields. Default Priority Medium, Client ID 0000.
- Use MCP-tools.md 快捷参数调用 MCP；无需读 schema。Duplicate check and post-create validation required.

## Output

Before create: **Ticket Name List**, **Confirmation Needed: Yes**.

After create: **Issue**, **URL**, **Type: Technical Story**, **Component**, **Assignee**, **Project**, **Validation**, **Validation Details**.
