---
name: create-story
description: Create Jira Story tickets for the CP team. Use when user asks to create a Story, story ticket, or user story. Prefer running scripts/jira/create_story.py (preflight + assemble + create + post-check). If user mentions Backlog, Sprint is not required. Supports linking the new Story to a PIN ticket (关联到 PIN-xxx) via issue link "Relates".
---

# Create Story

## Purpose

Create Jira **Story** tickets using workspace config and **Story-only** field structure.

## Config (read first)

- `Jira/assets/global/profile.yaml`: `me.default_project` when project not specified.
- `Jira/assets/project/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`, `ticketing.supported_work_types`, `ticketing.defaults.assignee`, `ticketing.defaults.client_id`.
- **Structure**: `Jira/policy/<project>/issue-structures/story.yaml` — required_fields, optional_fields, field_options, field_defaults.
- `Jira/policy/<project>/ticket-naming.yaml`: `naming.Story` for title format.
- `Jira/assets/global/epic-list.yaml`: `recent_epics` (filter by project key) to resolve Parent.
- `Jira/assets/project/<project>/sprint-list.yaml`: sprint format and `recent_sprints`.
- `Jira/assets/global/label-list.yaml`: roadmap/cross_team and `recent_labels`.

## 执行方式（脚本优先）

- **优先使用脚本**：`scripts/jira/create_story.py`
  - 已包含：重复检查、Parent 自动解析、required fields 拼接、创建、创建后校验、可选 PIN 关联。
  - 常用参数：`--project`、`--issue-type Story`、`--summary`、`--components`、`--priority`、`--parent`、`--dry-run`、`--allow-duplicate`、`--link-pin PIN-1,PIN-2`。
- **查询统一脚本化**：所有查询步骤优先用 `scripts/jira/query_issues.py --jql "<JQL>"`
- **仅在脚本不可用时**，才按 **`skills/ticket-management/MCP-tools.md`** 走手动 MCP 流程。

## Required inputs

1. Summary (normalized per naming below)
2. Component (from `workspace.ownership.components`)
3. Assignee (required; default from `ticketing.defaults.assignee` if missing)
4. All required fields from `issue-structures/story.yaml`: Story Type, Priority, Components, Labels, Client ID, Parent, UX Review Required?. **Sprint**: required only when the story is not for Backlog; if user says "Backlog" or "放到 Backlog", do not ask for or set Sprint.
5. Description: optional; if provided use Story template in `skills/ticket-management/ticket-templates/templates.md`.
6. **PIN 关联**（可选）：用户说「关联到 PIN-xxx」「link to PIN-2712」等时，创建命令使用 `--link-pin PIN-1,PIN-2`（逗号分隔）传入一个或多个 PIN key，创建后为该 Story 与这些 PIN 工单建立 **Relates** 类型的 issue link。PIN key 格式为 `PIN-<数字>`。

Apply `field_defaults` from story.yaml when user does not specify (Story Type = Improvement, Client ID = 0000, UX Review Required? = No, UX Review Status = Not Needed).

## Title / summary

Enforce format from `ticket-naming.yaml`: **`[模块] - [平台或范围] - [动作 + 对象]`**.

- 模块: component in brackets e.g. `[SOV]`, `[My Report]`.
- 平台或范围: `All Platforms` or slash e.g. `Amazon/Walmart/Target`.
- 动作 + 对象: formal wording; prefer `<业务主体> + <动作> + <对象>`; avoid colloquial phrases.
- If user summary does not match, rewrite to this format, show in Ticket Name List, get confirmation before create.

## Workflow

1. **Collect inputs**: summary, components, project (optional), plus optional `--link-pin` / `--parent` / `--priority`.
2. **Ticket Name List + confirmation**: 确认最终标题后再执行创建。
3. **先 dry-run**：运行 `python3 scripts/jira/create_story.py ... --dry-run`，查看 preflight（重复/parent/payload）。
4. **再创建**：运行同一命令去掉 `--dry-run`。如确认允许重复，追加 `--allow-duplicate`。
5. **PIN 关联**：若用户给 PIN key，创建命令追加 `--link-pin PIN-1,PIN-2`（逗号分隔），脚本会在创建后逐个建立 Relates。
6. **输出**：返回 issue key、URL、关键字段校验结果、以及 PIN link 状态（如有）。

## PIN Ticket 关联能力

- **何时使用**：用户创建 Story 时明确提到「关联到 PIN-xxx」「link to PIN-2712」等，表示该 Story 对应某条 PIN（Product Intake）工单，需在创建后建立 Jira issue link。
- **操作**：Story 创建成功后，调用 **`jira_create_issue_link`**（server: user-mcp-atlassian），`link_type` = **"Relates"**，`inward_issue_key` = 新创建的 Story key，`outward_issue_key` = 用户给出的 PIN key（格式 `PIN-<数字>`）。Jira 实例中该 link type 的正式名称为 **"Relates"**（不是 "Relates to"）。
- **输出**：在创建结果中注明「已与 PIN-xxx 建立 Relates 链接」。若需确认当前实例支持的 link type，可调用 **`jira_get_link_types`**。

## Guardrails

- Only components in `workspace.ownership.components`. Validate assignee; verify external before use.
- Pre-create Ticket Name List and explicit confirmation. No raw summary; always normalized title.
- Follow `issue-structures/story.yaml`; do not invent fields. Default Priority Medium, Client ID 0000.
- 优先用 `scripts/jira/create_story.py`；查询统一用 `scripts/jira/query_issues.py --jql "<JQL>"`，不要手动拼 MCP 查询/创建参数；仅脚本不可用时退回 MCP-tools.md。
- **PIN 关联**：用户指定 PIN key（如 PIN-2712）时，创建 Story 后必须调用 `jira_create_issue_link`，link_type 为 **"Relates"**（不是 "Relates to"）；inward=新 Story，outward=PIN。

## Output

Before create: **Ticket Name List**, **Confirmation Needed: Yes**.

After create: **Issue**, **URL**, **Type: Story**, **Component**, **Assignee**, **Project**, **Validation**, **Validation Details**. 若用户指定了 PIN 关联，输出中需包含 **PIN Link**: 已与 PIN-xxx 建立 Relates 链接。
