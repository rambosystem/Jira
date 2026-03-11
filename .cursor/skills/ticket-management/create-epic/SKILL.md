---
name: create-epic
description: Create Jira Epic tickets for the CP team. Use when user asks to create an Epic, quarterly epic, or Qn Module epic. Reads structure from issue-structures/epic.yaml; uses team and label-list.
---

# Create Epic

## Purpose

Create Jira **Epic** tickets using workspace config and **Epic-only** field structure.

## Config (read first)

- `Jira/Assets/Global/profile.yaml`: `me.default_project` when project not specified.
- `Jira/assets/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`, `ticketing.supported_work_types`, `ticketing.defaults.assignee_by_work_type.Epic`, `ticketing.defaults.client_id`.
- **Structure**: `Jira/Policy/<project>/issue-structures/epic.yaml` — required_fields, optional_fields, field_options, field_defaults.
- `Jira/Policy/<project>/ticket-naming.yaml`: `naming.Epic` for title format.
- `Jira/Assets/Global/epic-list.yaml`: conventions and recent_epics (for duplicate check).
- `Jira/assets/global/label-list.yaml`: roadmap and `recent_labels`.

## MCP 工具链

创建与校验 Epic 时用到的 Jira/Atlassian MCP 工具见 **`skills/ticket-management/MCP-tools.md`**（重复检查、用户校验、自定义字段、创建工单、创建后校验）。**直接按 MCP-tools.md 的「快捷参数」表传参即可，无需再读 mcps 下 descriptor。**

## Required inputs

1. Summary (prefer Epic naming below)
2. Component (from `workspace.ownership.components`)
3. Assignee (required; default `ticketing.defaults.assignee_by_work_type.Epic` for Epic if missing)
4. All required fields from `issue-structures/epic.yaml`: Priority, Components, Labels, Delivery Quarter.
5. Description: optional; if provided use Epic template in `skills/ticket-management/ticket-templates/templates.md`.

Apply `field_defaults` from epic.yaml (Client ID = 0000) when needed.

## Title / summary

Prefer format from `ticket-naming.yaml`: **`<Module> Upgrade - <YYQn>`** (e.g. `SOV Upgrade - 26Q2`).

- Shorthand "Q2 SOV epic" => Component from module, Delivery Quarter from quarter, Summary = `<Module> Upgrade - <YYQn>`, Labels include `roadmap_26q2` (roadmap_YYqN).

## Workflow

1. **Project**: From user or `me.default_project`. Ensure Epic is in `ticketing.supported_work_types`.
2. **Validate**: Component in ownership; assignee in team or external (verify via **`jira_get_user_profile`** or Confluence user search; add to `team.external_members` if new). All Epic required fields present; validate Delivery Quarter (Q1–Q4) and field_options.
3. **Labels**: Roadmap `roadmap_YYqN` from quarter; add `cross-team` if needed. Prefer `recent_labels`.
4. **Duplicate check** (**`jira_search_issues`**): Search same project + Epic + summary; for quarterly naming check existing `<Module> Upgrade - <YYQn>`. If exists, ask reuse or new.
5. **Ticket Name List**: List summary(ies); ask explicit confirmation.
6. **Assignee**: Prefer email → name → account_id. For Epic missing assignee use `assignee_by_work_type.Epic`.
7. **Custom fields** (**`jira_search_fields`**): Resolve Delivery Quarter, Epic Name; set via `additional_fields`.
8. **Create** (**`jira_create_issue`**): Project, type Epic, Summary, Assignee, Component, optional Description, Delivery Quarter (and Epic Name if used).
9. **Post-create** (**`jira_get_issue`** / **`jira_get_issue_by_key`**): Verify Summary, Type, Assignee, Priority, Components, Labels, Delivery Quarter; report PASS/FAIL.

## Guardrails

- Only components in `workspace.ownership.components`. Validate and verify external assignee.
- Pre-create Ticket Name List and explicit confirmation.
- Follow `issue-structures/epic.yaml`; do not invent fields. Default Priority Medium, Client ID 0000.
- Use MCP-tools.md 快捷参数调用 MCP；无需读 schema。Duplicate check and post-create validation required.
- Use `<Module> Upgrade - <YYQn>` unless user explicitly requests different naming.

## Output

Before create: **Ticket Name List**, **Confirmation Needed: Yes**.

After create: **Issue**, **URL**, **Type: Epic**, **Component**, **Assignee**, **Project**, **Validation**, **Validation Details**.
