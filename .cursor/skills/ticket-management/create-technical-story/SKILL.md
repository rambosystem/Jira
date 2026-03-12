---
name: create-technical-story
description: Create Jira Technical Story tickets for the CP team. Use when user asks to create a Technical Story or tech story. Prefer running scripts/jira/create_story.py with --issue-type "Technical Story" (preflight + assemble + create + post-check). Supports linking to a PIN ticket (关联到 PIN-xxx) via issue link "Relates".
---

# Create Technical Story

## Purpose

Create Jira **Technical Story** tickets using workspace config and **Technical Story-only** field structure.

## Config (read first)

- `Jira/assets/global/profile.yaml`: `me.default_project` when project not specified.
- `Jira/assets/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`, `ticketing.supported_work_types`, `ticketing.defaults.assignee`, `ticketing.defaults.client_id`.
- **Structure**: `Jira/policy/<project>/issue-structures/technical-story.yaml` — required_fields, optional_fields, field_options, field_defaults.
- `Jira/policy/<project>/ticket-naming.yaml`: `naming.Technical Story` (inherits Story format).
- `Jira/assets/global/epic-list.yaml`: `recent_epics` (filter by project key) to resolve Parent.
- `Jira/assets/<project>/sprint-list.yaml`: sprint format and `recent_sprints`.
- `Jira/assets/global/label-list.yaml`: roadmap/cross_team and `recent_labels`.

## 执行方式（脚本优先）

- **优先使用脚本**：`scripts/jira/create_story.py --issue-type "Technical Story"`
  - 先执行一次：`python3 scripts/policy/build_policy_json.py`（将 YAML/配置预编译为 `tmp/policy.resolved.json`）。
  - 已包含：重复检查、Parent 自动解析、required fields 拼接、创建、创建后校验、可选 PIN 关联。
  - Technical Story 关键参数：`--technical-story-type`（默认 `Code Quality`）。
- **仅在脚本不可用时**，才按 **`skills/ticket-management/MCP-tools.md`** 走手动 MCP 流程。

## Required inputs

1. Summary (normalized per naming below)
2. Component (from `workspace.ownership.components`)
3. Assignee (required; default from `ticketing.defaults.assignee` if missing)
4. All required fields from `issue-structures/technical-story.yaml`: Technical Story Type, Sprint, Priority, Components, Labels, Client ID, Parent.
5. Description: optional; if provided use Story template in `skills/ticket-management/ticket-templates/templates.md`.
6. **PIN 关联**（可选）：用户说「关联到 PIN-xxx」时，创建命令使用 `--link-pin PIN-1,PIN-2`（逗号分隔）传入一个或多个 PIN key，创建后为该 Technical Story 与这些 PIN 建立 **Relates** 链接；用法同 create-story，见 MCP-tools.md 的 jira_create_issue_link。

Apply `field_defaults` from technical-story.yaml (Client ID = 0000) when user does not specify.

## Title / summary

Same as Story (from `ticket-naming.yaml`): **`[模块] - [平台或范围] - [动作 + 对象]`**.

- 模块: component in brackets. 平台或范围: `All Platforms` or slash. 动作 + 对象: formal wording; prefer domain-subject style; avoid colloquial.
- If user summary does not match, rewrite, show in Ticket Name List, get confirmation before create.

## Workflow

1. **Collect inputs**: summary, components, project (optional), `--technical-story-type` (optional), plus optional `--link-pin` / `--parent` / `--priority`.
2. **Ticket Name List + confirmation**: 确认最终标题后再执行创建。
3. **先 build policy JSON**：运行 `python3 scripts/policy/build_policy_json.py`（当 policy/assets 变更后需重新执行）。
4. **再 dry-run**：运行 `python3 scripts/jira/create_story.py --issue-type "Technical Story" ... --dry-run`，查看 preflight。
5. **再创建**：去掉 `--dry-run`；如需允许重复，追加 `--allow-duplicate`。
6. **PIN 关联**：若用户给 PIN key，命令追加 `--link-pin PIN-1,PIN-2`（逗号分隔），脚本自动逐个建立 Relates。
7. **输出**：返回 issue key、URL、关键字段校验结果、以及 PIN link 状态（如有）。

## Guardrails

- Only components in `workspace.ownership.components`. Validate and verify external assignee.
- Pre-create Ticket Name List and explicit confirmation. Always normalized title.
- Follow `issue-structures/technical-story.yaml`; do not invent fields. Default Priority Medium, Client ID 0000.
- 优先用 `scripts/jira/create_story.py --issue-type "Technical Story"`，不要手动拼 MCP 创建参数；仅脚本不可用时退回 MCP-tools.md。
- **PIN 关联**：用户指定 PIN key 时，创建后调用 `jira_create_issue_link`，link_type = **"Relates"**；inward = 新工单 key，outward = PIN key。

## PIN Ticket 关联能力

与 create-story 一致：用户说「关联到 PIN-xxx」时，创建后调用 **`jira_create_issue_link`**（link_type **"Relates"**）。详见 **create-story/SKILL.md** 的「PIN Ticket 关联能力」与 **MCP-tools.md** 的 jira_create_issue_link 表。

## Output

Before create: **Ticket Name List**, **Confirmation Needed: Yes**.

After create: **Issue**, **URL**, **Type: Technical Story**, **Component**, **Assignee**, **Project**, **Validation**, **Validation Details**. 若指定了 PIN 关联，输出 **PIN Link**: 已与 PIN-xxx 建立 Relates 链接。
