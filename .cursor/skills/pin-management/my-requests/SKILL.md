---
name: my-requests
description: 查询 PIN 项目中分配给当前用户（profile 中 me.account_id）、且状态为 Ready for Technical Review 的工单，按状态分组展示。用户说「my pin tickets」「未处理的 pin ticket」「my requests」时使用。
---

# My Requests（未处理 Pin 工单）

## Purpose

查询 **PIN** 项目（Product Intake）中分配给 **我**（`profile.yaml` 的 `me.account_id`）、且处于 **Ready for Technical Review** 的工单（视为当前要处理的「未处理」口径），按状态分组展示。

**Backlog**：是否纳入本 Skill 的查询范围 **待定**；当前版本 **不包含** Backlog，仅查 Ready for Technical Review。

## Workflow

1. **Assignee**：从 `config/assets/global/profile.yaml` 读取 `me.account_id`，用于 JQL。
2. **JQL**（状态名须与 Jira 工作流一致，一般为 `Ready for Technical Review`）：
   ```
   project = PIN AND assignee in ("<me.account_id>") AND status = "Ready for Technical Review" ORDER BY priority DESC, created DESC
   ```
3. **调用 Jira**：MCP `user-mcp-atlassian` · `jira_search`，传入上述 JQL；`fields` = `key,summary,status,assignee,updated,priority,created`；`limit` = 50。
4. **展示**：按 **status** 分组（当前通常仅一组），每组下表格式：key、summary、priority、updated；文末总条数 + 一句「以上为你在 PIN 项目中处于 Ready for Technical Review 且分配给你的工单。」无结果时提示「当前没有处于 Ready for Technical Review 的 Pin ticket。」
5. **可选**：问用户是否要生成 Summary Report；若肯定则按 request-pin-report 技能处理（默认用当前列表全部 PIN）。

## 约定

- 必须用 profile 的 `me.account_id` 作为 assignee，不用 `currentUser()`。
- 项目 key 为 **PIN**；仅展示接口返回的工单，不杜撰。
- **Backlog** 工单不在本 Skill 查询范围内（待定是否后续纳入）；若 Jira 中状态名称与上述不一致，以实例为准调整 JQL 中的 `status` 字符串。
