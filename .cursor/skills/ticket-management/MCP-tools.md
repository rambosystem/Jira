# MCP 工具链（ticket-management）

创建与校验 Story、Technical Story、Epic 时用到的 Jira/Atlassian MCP 工具。实际工具名以当前启用的 MCP server（如 user-mcp-atlassian）提供的为准；若与下表不同，请以 MCP 描述为准并在此文档中维护对应关系。

> 执行优先级：当可用时，先用脚本 `scripts/jira/create_story.py`（含 preflight + create + post-check）；MCP 表用于脚本不可用时的 fallback 或补充操作。

- **Confluence 页面创建/更新、搜索、附件等**：见 **`skills/confluence-management/MCP-tools.md`**。

## 工具与流程对应

| 流程环节   | 用途                                                                 | MCP 工具                                         | 说明                                                                                                                        |
| ---------- | -------------------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| 重复检查   | 按项目 + 类型 + Summary 查是否已有同款工单                           | `jira_search`                                    | 入参：JQL（如 project + issuetype + summary）；用于 Duplicate check 步骤                                                    |
| 用户校验   | 外部 assignee 是否存在、获取 accountId/email                         | `jira_get_user_profile` 或 Confluence 用户搜索类 | 入参：email/username/accountId；Assignee 不在 team 内时调用。可选用 Confluence 用户搜索与 Jira 用户查询组合                 |
| 自定义字段 | 解析 customfield_xxxxx 以写入 Parent、Client ID、Delivery Quarter 等 | `jira_search_fields`                             | 需解析的字段名：Parent、Client ID、Delivery Quarter、Epic Name、UX Review Required?、UX Review Status 等（按 issue 类型）   |
| 创建工单   | 创建 Story / Technical Story / Epic                                  | `jira_create_issue`                              | 入参：projectKey、issueType、summary、assignee、description、additional_fields（含 parent、customfield_xxx）等              |
| 创建后校验 | 读取刚创建的 issue 核对字段                                          | `jira_get_issue` / `jira_get_issue_by_key`       | 用返回的 issue key 拉取详情，核对 Summary、Type、Assignee、Priority、Components、Labels、Parent、Sprint 或 Delivery Quarter |
| **PIN 关联** | 将新建的 CP Story 与 PIN 工单建立「关联」                           | `jira_create_issue_link`                         | 创建后若用户指定「关联到 PIN-xxx」，用 link_type **"Relates"**（Jira 中名称是 Relates，不是 "Relates to"）；inward=Story key，outward=PIN key |

## 快捷参数（免读 schema）

**Server** 均为 `user-mcp-atlassian`。创建/校验流程可直接按下表调用，无需再读 mcps 下 descriptor。

| 工具                      | 必填参数                                      | 可选参数                                                                                                                                          |
| ------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **jira_search**           | `jql`                                         | `fields`（默认含 status, summary 等）, `limit`（1–50，默认 10）                                                                                   |
| **jira_get_user_profile** | `user_identifier`（email/username/accountId） | —                                                                                                                                                 |
| **jira_search_fields**    | —                                             | `keyword`（模糊搜字段名）, `limit`（默认 10）, `refresh`                                                                                          |
| **jira_create_issue**     | `project_key`, `summary`, `issue_type`        | `assignee`, `description`, `components`（逗号分隔）, `additional_fields`（**JSON 字符串**，如 `"{\"parent\": \"CP-123\", \"labels\": [\"x\"]}"`） |
| **jira_get_issue**        | `issue_key`                                   | `fields`, `expand`, `comment_limit`（默认 10）                                                                                                    |
| **jira_create_issue_link** | `link_type`, `inward_issue_key`, `outward_issue_key`（**三者必填，不可省略或传空**） | `comment`, `comment_visibility`                                                                                                                                 |
- **PIN 关联**：与 PIN 工单建立「关联」时，`link_type` 填 **"Relates"**；`inward_issue_key` = 刚创建的 Story key（如 CP-45995），`outward_issue_key` = PIN key（如 PIN-2712）。可用 **`jira_get_link_types`** 查询当前实例支持的 link type 列表。
- **禁止**：不可用空对象 `{}` 或省略任一必填参数调用 `jira_create_issue_link`，否则会报 `Missing required argument` 校验错误。
- **重复检查**：用 **jira_search** + JQL（如 `project = CP AND issuetype = Story AND summary ~ "..."`），无需 `jira_search_issues`。
- **Parent 格式**：`additional_fields` 中 `parent` 必须为 issue key 字符串，例如 `"parent": "CP-123"`，不要传对象。

## 调用约定

- **创建/校验流程**：直接使用上表快捷参数调用 MCP，无需读 mcps 下 descriptor。
- **Parent 格式**：在 `jira_create_issue` 的 `additional_fields` 中，`parent` 必须为 issue key **字符串**，例如 `"parent": "CP-123"`。不要传对象（如 `{"key": "CP-123"}`），否则会报错。
- **jira_create_issue_link**：每次调用必须显式传入 `link_type`、`inward_issue_key`、`outward_issue_key` 三个参数，不得传空对象或省略，否则会触发 Pydantic 校验错误（Missing required argument）。

## CP/PAG 创建工单 additional_fields 参考（一次拼好、避免重试）

创建前按本表拼好 `additional_fields` JSON 字符串，**必填自定义字段一次带齐**，避免「Story Type is required」「Client ID」等报错。

### Story（CP / PAG）

| 显示名 | key | 传参格式 | 示例/默认 |
|--------|-----|----------|-----------|
| Priority | priority | `{"name": "Medium"}` | 必填 |
| Parent (Epic) | parent | 字符串 issue key | `"CP-45460"` |
| Client ID | customfield_10043 | **字符串数组** | `["0000"]` |
| Story Type | customfield_10085 | `{"value": "Improvement"}` | 必填，默认 Improvement |
| UX Review Required? | customfield_13319 | `{"value": "No"}` | 默认 No |
| UX Review Status | customfield_13320 | `{"value": "Not Needed"}` | 默认 Not Needed |

**示例（Backlog、默认值）**：  
`{"priority": {"name": "Medium"}, "parent": "CP-45460", "customfield_10043": ["0000"], "customfield_10085": {"value": "Improvement"}, "customfield_13319": {"value": "No"}, "customfield_13320": {"value": "Not Needed"}}`  
Sprint 放 Backlog 时不传 Sprint；要进 Sprint 时再在 additional_fields 中加 customfield_10020（格式以 jira_search_fields 或 createmeta 为准）。

### Technical Story（CP / PAG）

| 显示名 | key | 传参格式 |
|--------|-----|----------|
| Priority | priority | `{"name": "Medium"}` |
| Parent | parent | issue key 字符串 |
| Client ID | customfield_10043 | `["0000"]` |
| Technical Story Type | customfield_12348 | `{"value": "Code Quality"}` 等（见 issue-structures/technical-story.yaml field_options） |

### Epic（CP / PAG）

| 显示名 | key | 传参格式 |
|--------|-----|----------|
| Priority | priority | `{"name": "Medium"}` |
| Delivery Quarter | customfield_12899 | `{"value": "Q1"}` 等 |
| Components | 用 jira_create_issue 的 components 参数 | 逗号分隔名称 |

**流程优化要点**：① 先做重复检查（jira_search）② Parent 从 epic-list 按 component/quarter 解析 ③ 按上表拼齐 additional_fields 再调 jira_create_issue ④ 创建后 jira_get_issue 校验。
