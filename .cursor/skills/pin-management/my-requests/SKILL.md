---
name: my-requests
description: Query unprocessed Pin tickets assigned to me (from Jira/Assets/Global/profile.yaml) in the PIN/Product Intake project; present results grouped by status. Use when the user asks for "my pin tickets", "未处理的 pin ticket", "my requests", or to list open/outstanding pin requests in Product Intake.
---

# My Requests（未处理的 Pin Ticket）

## Purpose

Query and list **unprocessed Pin tickets** in the **PIN** project (Product Intake Service Desk) that are assigned to **me** (the workspace user from `Jira/Assets/Global/profile.yaml` → `me.account_id`). PIN 工单示例: `PIN-1464`.

## When to Use

- User asks for "我的 pin ticket" or "未处理的 pin ticket"
- User asks for "my requests" or "my pin requests" in PIN / Product Intake
- User wants to see open/outstanding pin tickets they need to handle

## Configuration to Read

1. **`Jira/Assets/Global/profile.yaml`** — **required**
   - Read **`me`** from this file. Use **`me.account_id`** as the assignee in JQL (Jira/Atlassian 用户标识). Do not use `currentUser()`; always substitute `me.account_id` from profile so "my requests" is the workspace user (e.g. Rambo Wang).
   - Fallback: if `me.account_id` is missing, use `me.email` and resolve to accountId via Jira user lookup if needed.

2. **Project**: **PIN** — Jira Service Desk project (Product Intake). Base URL: `https://pacvue-enterprise.atlassian.net/jira/servicedesk/projects/PIN/`. Issue keys are like `PIN-1464`.

## Workflow

1. **Resolve assignee from profile**
   - Read **`Jira/Assets/Global/profile.yaml`** and get **`me.account_id`**. Use this value in the JQL assignee condition (e.g. `assignee in ("<me.account_id>")`).

2. **JQL (My Requested)**
   - Build JQL by substituting **`<me.account_id>`** with the value from `profile.yaml` → `me.account_id`:

   ```
   project = PIN AND assignee in ("<me.account_id>") AND status IN ("Backlog", "Ready for Technical Review") ORDER BY priority DESC, created DESC
   ```

3. **Call Jira MCP**（无需再读 schema，直接按下列参数调用）
   - **Server**: `user-mcp-atlassian` · **Tool**: `jira_search`
   - **Arguments**: `jql` = 上一步拼好的 JQL（已代入 `me.account_id`）；`fields` = `key,summary,status,assignee,updated,priority,created`；`limit` = `50`（可选，默认 10）。
   - 直接调用 `call_mcp_tool(server="user-mcp-atlassian", toolName="jira_search", arguments={...})` 即可。

4. **Present results**
   - **Group by status**: Present issues grouped by **status** (status name as section heading). Within each group, keep the order as returned by JQL. Each group shows a table: key, summary, priority, updated.
   - Use headings like `### Accepted for Development`, `### Ready for Technical Review`, `### Backlog`, `### Waiting on Reporter`, etc., one per status that appears in the result set.
   - Include total count and a short line like "以上为你在 PIN (Product Intake) 项目中未处理的 Pin 工单。"

5. **Ask whether to generate Summary Report (Optional)**
   - After presenting results, **ask the user**: "是否要生成 Summary Report？"（或英文："Would you like to generate a Summary Report?"）
   - **If the user says yes**（如回答「要」「是」「生成」「yes」「generate」等）：按 **`skills/pin-management/request-pin-report/SKILL.md`** 执行 Request PIN Report 工作流。
     - **默认**：对**当前展示的列表中的全部** PIN 工单生成报告（传入本步骤 3 返回的所有 issue 的 key 列表）。
     - **仅当用户明确指定**某一或若干 PIN Key（如「只生成 PIN-1234」「只要 PIN-2677 和 PIN-2680」）时，仅对用户指定的工单生成报告。
   - **If the user says no or does not answer affirmatively**：结束，不再调用 request-pin-report。

## Output Format

- **Reply**: Group results **by status**; under each status heading, show a table with key, summary, **priority**, updated. Then total count and one-line summary in Chinese.
- If no issues found: "当前没有未处理的 Pin ticket。" or "No unprocessed pin tickets found."

## Guardrails

- **Assignee**: Always use **`me.account_id`** from `Jira/Assets/Global/profile.yaml` in the JQL; do not use `currentUser()` so that "my requests" is the workspace user (profile me).
- Only include issues returned by the Jira query; do not invent tickets.
- For this skill, use the inline MCP params above; no need to read schema from mcps folder.
- Project key is **PIN** (Product Intake Service Desk). Do not substitute other keys.
- If the ID obtained from profile.me is assigned to me by default, please do not ask again whether to only query the ID assigned to me.
