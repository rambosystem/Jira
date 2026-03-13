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
7. **Roadmap Quarter** — 路线图季度，必填；如 Q2 填 `26Q2`，Q1 填 `26Q1`（格式以 Jira 项目选项为准）。

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
2. **Collect**: summary, description（或按模板生成）, assignee（默认 profile.me）, Release Status（默认 Discovery）, **Roadmap Quarter**（用户指定，如 Q2 → 26Q2）。
3. **Build additional_fields**（JSON 字符串）**仅包含必填自定义字段**：
   - `customfield_10278` (Teams): `[{"value": "Ads"}]` 或等价结构（依 Jira API 要求）。
   - `customfield_10508` (Client Segment): `[{"value": "Pacvue"}]`。
   - `customfield_10726` (Release Status): `{"value": "Discovery"}` 或用户指定值。
   - `customfield_12866` (Roadmap Quarter): 多选，如 `["26Q2"]` 或 `[{"value": "26Q2"}]`（格式以 Jira API 为准；用户说 Q2 时传 26Q2）。
4. **Call** MCP `user-mcp-atlassian` · **`jira_create_issue`**:
   - `project_key`: **PACID**
   - `issue_type`: **Idea**
   - `summary`: 用户确认的标题
   - `description`: 按模板填好的 ADF 或 Markdown（若 API 接受 Markdown 则直接传）
   - `assignee`: 用户指定或 profile 的 email/accountId
   - `additional_fields`: 上述四个必填自定义字段（Teams、Client Segment、Release Status、**Roadmap Quarter**）。注意 Jira Cloud 对 option/array 的格式要求，可参考 createmeta。
5. **Output**: 返回 created issue key、URL、Summary、Assignee、Release Status、Roadmap Quarter、以及已填的自定义字段摘要。
6. **询问用户**：「是否为该 Idea 创建对应的 Epic 并关联到 Idea 的 Delivery？」若用户同意，执行下方「为 Idea 创建并关联 Epic」流程。

---

## Idea 的 Delivery 关联方式（供关联 Epic 时使用）

- **含义**：Jira Product Discovery (Polaris) 中，Idea 的 **Delivery** 面板用于展示「实现该 Idea 的 Jira 工作项」（Epic、Story 等）；关联后 Delivery progress/status 会基于已链接工作项自动计算。
- **实现方式**：通过 **issue link** 将 Jira 工作项（如 CP Epic）与 PACID Idea 链接。链接类型为 **"Polaris work item link"**（outward = implements，inward = is implemented by）。
- **建链规则**：**Epic 为 outward（implements）**，**Idea 为 inward（is implemented by）**。即：`jira_create_issue_link(link_type="Polaris work item link", inward_issue_key=<PACID Idea key>, outward_issue_key=<CP Epic key>)`。这样 Epic 会出现在该 Idea 的 Delivery 面板中。

## 为 Idea 创建并关联 Epic（用户确认后执行）

1. 按 **create-epic** 技能为当前 Idea 创建一条 CP Epic（Summary 可与 Idea 对齐或按 `<Module> Upgrade - <YYQn>`；Component、Delivery Quarter 等由用户指定或从 Idea 的 Roadmap Quarter 推断）。
2. 创建 Epic 成功后，调用 **`jira_create_issue_link`**（server: user-mcp-atlassian）：
   - `link_type`: **"Polaris work item link"**
   - `inward_issue_key`: 刚创建的 **PACID Idea key**（如 PACID-6116）
   - `outward_issue_key`: 刚创建的 **CP Epic key**（如 CP-4xxxx）
3. 可选：按 create-epic 技能更新 **Epic List**（`Assets/Global/epic-list.yaml` 的 recent_epics 顶部加入新 Epic）。
4. 告知用户：已创建 Epic、已关联到 Idea 的 Delivery、Epic key 与链接状态。

## Field keys（仅必填，创建时只传以下四项自定义字段）

| 显示名           | Key               | 说明 |
|------------------|-------------------|------|
| Teams            | customfield_10278  | array, 固定 Ads |
| Client Segment   | customfield_10508  | array, 固定 Pacvue |
| Release Status   | customfield_10726  | option: Discovery, Development, Alpha, Beta, GA, Product Backlog |
| Roadmap Quarter  | customfield_12866  | array (multicheckboxes)，如 26Q2；用户说 Q2 时必填 |

具体 option/array 的 id/value 以 `docs/pacid-createmeta.json` 或 Jira API 返回为准。

## Guardrails

- 项目固定为 **PACID**，issue_type 固定为 **Idea**。
- **只传** `idea-middle-platform.yaml` 中 `required_by_team` 的字段；非必填字段一律不传。
- 不杜撰字段 key。
- Assignee 未指定时用 profile 的 `me.account_id` 或 `me.email`。
- Description 必须包含 template 中五段结构（可部分待补充），不要只写一句纯文本。
- 将 Epic 关联到 Idea 的 Delivery 时，必须使用 **Polaris work item link**：inward = PACID Idea key，outward = CP Epic key。

## Output

- **Before create**: 列出 Summary、Assignee、Release Status、**Roadmap Quarter**、Description 是否按模板，请用户确认。
- **After create**: **Issue key**、**URL**、**Summary**、**Assignee**、**Release Status**、**Roadmap Quarter**、**Client Segment**、**Teams**；并**询问**：「是否为该 Idea 创建对应的 Epic 并关联到 Idea 的 Delivery？」若用户同意，按「为 Idea 创建并关联 Epic」流程执行。
