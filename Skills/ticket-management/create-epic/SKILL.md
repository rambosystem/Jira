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
- `Jira/Assets/Global/delivery-quarter.yaml`: `field_id`, `options`, `default_rule`, `roadmap_label_alignment` — use for Delivery Quarter 流程，勿再对 Delivery Quarter 调 `jira_search_fields`。
- `Jira/assets/global/label-list.yaml`: roadmap and `recent_labels`.

## MCP 工具链

创建与校验 Epic 时用到的 Jira/Atlassian MCP 工具见 **`skills/ticket-management/MCP-tools.md`**（重复检查、用户校验、自定义字段、创建工单、创建后校验）。调用前必读该工具的 schema。

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

## Delivery Quarter

1. **字段来源**：从 `Jira/Assets/Global/delivery-quarter.yaml` 读取 `field_id`（如 customfield_12899）、`options`（Q1–Q4）。不再对 “Delivery Quarter” 调用 `jira_search_fields`。
2. **取值优先级**：用户明确指定季度 > 从 Summary 中的 `<YYQn>` 解析出 Qn > 按 `default_rule` 取当前季度（可结合 `label-list.yaml` 的 `recent_labels` 或当年当季）。
3. **与 Roadmap 一致**：Delivery Quarter 定为某季度（如 26Q1）时，`labels` 必须包含对应 `roadmap_YYqN`（如 `roadmap_26q1`），见 `delivery-quarter.yaml` 的 `roadmap_label_alignment` 与 `label-list.yaml`。
4. **写入格式**：在 `jira_create_issue` 的 `additional_fields` 中写入 `{ "<field_id>": { "value": "Q1" } }`（Q1/Q2/Q3/Q4 其一），例如 `{"customfield_12899": {"value": "Q1"}}`。
5. **创建后校验**：用 `jira_get_issue` 拉取刚创建的 issue，在返回中核对该 `field_id` 的值与预期一致。

## Workflow

1. **Project**: From user or `me.default_project`. Ensure Epic is in `ticketing.supported_work_types`.
2. **Validate**: Component in ownership; assignee in team or external (verify via **`jira_get_user_profile`** or Confluence user search; add to `team.external_members` if new). All Epic required fields present; validate Delivery Quarter (Q1–Q4) and field_options.
3. **Labels**: Roadmap `roadmap_YYqN` from quarter; add `cross-team` if needed. Prefer `recent_labels`.
4. **Duplicate check** (**`jira_search_issues`**): Search same project + Epic + summary; for quarterly naming check existing `<Module> Upgrade - <YYQn>`. If exists, ask reuse or new.
5. **Ticket Name List**: List summary(ies); ask explicit confirmation.
6. **Assignee**: Prefer email → name → account_id. For Epic missing assignee use `assignee_by_work_type.Epic`.
7. **Delivery Quarter**：按上文「Delivery Quarter 流程」从 `delivery-quarter.yaml` 取 `field_id` 与取值，写入 `additional_fields`。其他自定义字段（如 Epic Name）若需再解析，可调 **`jira_search_fields`**。
8. **Create** (**`jira_create_issue`**): Project, type Epic, Summary, Assignee, Component, optional Description, `additional_fields` 含 Priority、Labels、Delivery Quarter（及 Epic Name 等若适用）。
9. **Post-create** (**`jira_get_issue`**): 用返回的 issue key 拉取详情，核对 Summary, Type, Assignee, Priority, Components, Labels，以及 `delivery-quarter.yaml` 中 `field_id` 对应字段（Delivery Quarter）；报告 PASS/FAIL。

## Guardrails

- Only components in `workspace.ownership.components`. Validate and verify external assignee.
- Pre-create Ticket Name List and explicit confirmation.
- Follow `issue-structures/epic.yaml`; do not invent fields. Default Priority Medium, Client ID 0000.
- Read Jira MCP tool schema before calling. Duplicate check and post-create validation required.
- Use `<Module> Upgrade - <YYQn>` unless user explicitly requests different naming.

## Output

Before create: **Ticket Name List**, **Confirmation Needed: Yes**.

After create: **Issue**, **URL**, **Type: Epic**, **Component**, **Assignee**, **Project**, **Validation**, **Validation Details**.
