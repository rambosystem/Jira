---
name: my-requests
description: Query unprocessed Pin tickets assigned to me (from Jira/Assets/Global/profile.yaml) in the PIN/Product Intake project. Use when the user asks for "my pin tickets", "未处理的 pin ticket", "my requests", or to list open/outstanding pin requests in Product Intake.
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
   project = PIN AND statusCategory != Done AND assignee in ("<me.account_id>") AND "Request Type" in ("API Scope Request", "New Feature Integration", "New RMN Request", "Partnership Request", "Product Feedback Request", "Suggest a new feature/Improvement - H10", "Suggest a new feature/improvement - Pacvue") ORDER BY created ASC, priority
   ```
   - **Request Type** values: API Scope Request, New Feature Integration, New RMN Request, Partnership Request, Product Feedback Request, Suggest a new feature/Improvement - H10, Suggest a new feature/improvement - Pacvue. Do not change unless the user requests it.

3. **Call Jira MCP**
   - Use **`jira_search`** (or equivalent JQL search tool) from the Atlassian MCP server. **Read the tool's schema/descriptor first** (see `skills/ticket-management/MCP-tools.md`) and pass the built JQL (with `me.account_id` substituted), `fields`, `limit`.
   - Request useful fields: `key`, `summary`, `status`, `assignee`, `updated`, `priority`, `created` (and `Request Type` if needed).

4. **Present results**
   - List each ticket: key, summary, status, updated (and optionally priority).
   - Include total count and a short line like "以上为你在 PIN (Product Intake) 项目中未处理的 Pin 工单。"

## Output Format

- **Reply**: Table or list of unprocessed pin tickets with key, summary, status, updated; total count; one-line summary in Chinese.
- If no issues found: "当前没有未处理的 Pin ticket。" or "No unprocessed pin tickets found."

## Guardrails

- **Assignee**: Always use **`me.account_id`** from `Jira/Assets/Global/profile.yaml` in the JQL; do not use `currentUser()` so that "my requests" is the workspace user (profile me).
- Only include issues returned by the Jira query; do not invent tickets.
- Call Jira MCP tool only after reading its schema for correct parameters.
- Project key is **PIN** (Product Intake Service Desk). Do not substitute other keys.
