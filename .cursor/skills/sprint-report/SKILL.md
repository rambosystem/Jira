---
name: sprint-report
description: Generate a Sprint completion report for Defenders team—query Jira for Done Stories in a given sprint, group by functional module, and write a 迭代总结 markdown file. Use when user asks for sprint report, sprint summary, 迭代总结, or "Sprint N 完成了哪些/按模块总结".
---

# Sprint Report（迭代总结）

## Purpose

Produce a **Sprint 迭代总结** document that:

- Lists all **completed (Done)** Stories in a specified Defenders sprint
- Groups them by **functional module** (component)
- Outputs a markdown file with section tables and a one-line **迭代要点** per module, plus a summary table

## When to Use

- User asks for "Sprint N 完成了哪些 Story" or "Sprint N 按模块总结"
- User asks for "迭代总结" or "Sprint Report" for a given sprint
- User wants a written summary of what was delivered in a sprint, by module

## Configuration to Read

1. **`Jira/config/assets/global/profile.yaml`**
   - `me.default_project`: project key when user does not specify (e.g. `CP`). Use this to resolve paths below.

2. **`Jira/config/assets/project/<project>/sprint-list.yaml`** (project from user or `me.default_project` from profile)
   - `sprint_management.format.template`: `<YYQn>-Sprint<1..6>-Defenders`
   - `sprint_management.recent_sprints.active_quarter`: e.g. `26Q1`
   - `sprint_management.recent_sprints.values`: list of sprint names (e.g. `26Q1-Sprint4-Defenders`)

3. **`Jira/config/assets/project/<project>/team.yaml`** (and optionally **`Jira/config/assets/project/<project>/components.yaml`**)
   - `workspace.project.key`: e.g. `CP`
   - **Canonical module list**: If `workspace.ownership.components_file` is set (e.g. `components.yaml`), read the list from that file (same dir as team.yaml); file has `components`: array of `{ name, last_version? }` or strings—use `name` or the string. Otherwise use `workspace.ownership.components`.

When querying Jira for board/sprint data, use **`Jira/config/assets/project/<project>/query-templates.yaml`** (e.g. `sprint_done_stories`) and substitute placeholders with values from `team.yaml` and the resolved sprint name.

## Resolving Sprint Name

- If user says **"Sprint4"** or **"Sprint 4"**: use `active_quarter` + `-Sprint4-Defenders` (e.g. `26Q1-Sprint4-Defenders`).
- If user gives full name (e.g. `26Q1-Sprint4-Defenders`): use as-is.
- If quarter is ambiguous, prefer `recent_sprints.active_quarter` from `Jira/config/assets/project/<project>/sprint-list.yaml`.

## Workflow

1. **Resolve sprint identifier**
- Determine project: from user input or `me.default_project` in `Jira/config/assets/global/profile.yaml`.
- From user input (e.g. "Sprint4") derive full sprint name (e.g. `26Q1-Sprint4-Defenders`) using `Jira/config/assets/project/<project>/sprint-list.yaml`.

2. **Query Jira**（无需读 schema，直接按下列参数调用）
   - **Server**: `user-mcp-atlassian` · **Tool**: `jira_search`
   - **JQL**: `project = <workspace.project.key> AND issuetype = Story AND sprint = "<sprint_name>" AND statusCategory = Done ORDER BY key ASC`（代入已解析的 project key 与 sprint 名称）
   - **Arguments**: `jql` = 上式；`fields` = `key,summary,status,assignee,components`；`limit` = `50`（或更大，按需）
   - 直接调用 `call_mcp_tool(server="user-mcp-atlassian", toolName="jira_search", arguments={...})` 即可。

3. **Group by module**
   - **Preferred**: group by issue `components` (use first component or primary component if multiple).
   - **Fallback**: infer module from summary:
     - Match pattern `[Module Name]` at the start (e.g. `[My Report]`, `[SOV]`, `[Calendar Center]`).
     - Or map known prefixes (e.g. "Creative Hub" / "Creative HUb" → Creative Management, "Dayparting" / "Dayparting Scheduler" → Dayparting Scheduler, "Crawl Task" + SOV → SOV).
   - Normalize module labels to match the project's component list (from components file or `workspace.ownership.components`) where possible (e.g. "Creative Hub" → "Creative Management").
   - Sort sections by a stable order: either by the project's component list order, or alphabetically by module name; put "其他" or uncategorized at the end.

4. **Build 迭代要点 per module**
   - For each module, write one short sentence (迭代要点) summarizing the theme of the completed work (e.g. "Kroger 新版本支持、Target 活动管理与快照能力"). Keep it concise and business-readable.

5. **Write markdown file**
   - **Filename**: `Sprint<N>-Defenders-迭代总结.md` (e.g. `Sprint4-Defenders-迭代总结.md`) or `<sprint_name>-迭代总结.md`.
   - **Structure** (follow this template):
     - Title: `# Sprint<N> Defenders 迭代总结（<sprint_name>）` or `# <sprint_name> 迭代总结`
     - Intro line: 已完成 Story 共 **N** 条，按功能模块汇总如下。
     - For each module: `## <Module>`, then table `| Key | 内容 |` with rows from completed issues, then `**迭代要点**：<one-line summary>`
     - **汇总** table: `| 模块 | 完成 Story 数 | 主要方向 |`
     - Footer: `*数据来源：Jira <project> 项目，Sprint = <sprint_name>，statusCategory = Done。*`

6. **Calling Jira**
   - For this skill, use the inline MCP params in step 2; no need to read schema from mcps folder.

## Output Format

- **Primary**: A markdown file in the workspace root (or a docs folder if the project has one), named as above.
- **Reply to user**: Short confirmation with file path, total Story count, and list of components with counts (e.g. "已生成 `Sprint4-Defenders-迭代总结.md`，共 20 条 Story，7 个模块：My Report(4), Dayparting(3), …").

## Guardrails

- Do not invent or guess completed issues; only include issues returned by the Jira query (Story + sprint + statusCategory = Done).
- If the sprint name cannot be resolved (e.g. "Sprint99"), ask the user for the exact sprint name or quarter.
- If zero issues are returned, still produce the markdown file with an empty body and a note that no completed Stories were found for that sprint.
- Prefer Jira `components` for grouping; use summary-based inference only when components are missing or empty.
- Keep 迭代要点 in Chinese, concise and consistent with the style in `Sprint4-Defenders-迭代总结.md`.

## Reference

- Example output: see workspace file `Sprint4-Defenders-迭代总结.md` for the exact section layout, table format, and 迭代要点 style.
