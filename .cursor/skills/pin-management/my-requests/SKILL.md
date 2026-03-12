---
name: my-requests
description: 查询 PIN 项目中分配给当前用户（profile 中 me.account_id）的未处理工单，按状态分组展示。用户说「my pin tickets」「未处理的 pin ticket」「my requests」时使用。
---

# My Requests（未处理 Pin 工单）

## Purpose

查询 **PIN** 项目（Product Intake）中分配给 **我**（`profile.yaml` 的 `me.account_id`）且状态为未处理的工单，按状态分组展示。

## Workflow

1. **Assignee**：从 `assets/global/profile.yaml` 读取 `me.account_id`，用于 JQL。
2. **JQL**：
   ```
   project = PIN AND assignee in ("<me.account_id>") AND status IN ("Backlog", "Ready for Technical Review") ORDER BY priority DESC, created DESC
   ```
3. **调用 Jira**：MCP `user-mcp-atlassian` · `jira_search`，传入上述 JQL；`fields` = `key,summary,status,assignee,updated,priority,created`；`limit` = 50。
4. **展示**：按 **status** 分组，每组下表格式：key、summary、priority、updated；文末总条数 + 一句「以上为你在 PIN 项目中未处理的工单。」无结果时提示「当前没有未处理的 Pin ticket。」
5. **可选**：问用户是否要生成 Summary Report；若肯定则按 request-pin-report 技能处理（默认用当前列表全部 PIN）。

## 约定

- 必须用 profile 的 `me.account_id` 作为 assignee，不用 `currentUser()`。
- 项目 key 为 **PIN**；仅展示接口返回的工单，不杜撰。
