---
name: request-pin-report
description: 根据 PIN 工单 ID 拉取 Jira 详情并生成「Request PIN Report」格式报告。用户说「生成 PIN 报告」「Request PIN Report」时使用；通常用户不会给链接，未指定 PIN ID 时先按 my-requests 获取其未处理工单列表再确定目标工单。
---

# Request PIN Report（根据 PIN ID 生成需求报告）

## Purpose

根据 **PIN 工单 Key**（如 `PIN-2677`）调用 Jira MCP 获取 issue 详情，生成固定格式的 **Request PIN Report**，并发布到 **Confluence**（目标来自 profile 的 `confluence_workspace`）。**仅一条**时在对话中直接回复报告正文并说明已发布到 Confluence；**多条**时不在对话中展示正文，仅说明已发布。

## When to Use

- User asks to generate a "Request PIN Report" or "PIN 需求报告"
- User provides a PIN issue key (e.g. `PIN-2677`) and wants a structured report
- User says "根据 PIN-xxxx 生成报告" 或 "把这个 PIN 整理成需求报告"

## Input

- **PIN 工单 Key（单个或多个）**：
  - 用户**明确给出**单个或若干 PIN Key（或链接）时，仅对这些 ID 生成报告。
  - 由 **my-requests** 传入的**工单列表**（未特别指定时）：对**列表全部**生成报告，无需用户再指定；仅当用户**特别指定**某一或若干 PIN 时，才只对指定的生成。

## Workflow

1. **解析或获取 PIN ID（单个或列表）**
   - **用户已指定**：从用户输入或链接中提取一个或多个 `PIN-xxxx`（如 `PIN-2677` 或「只生成 PIN-1234」），得到 PIN ID 列表后进入步骤 2。
   - **由 my-requests 传入且用户未特别指定**：使用 my-requests 刚返回的**全部**工单 key 作为 PIN ID 列表，进入步骤 2 一次性拉取详情，再对每个返回的 issue 执行步骤 3～5。
   - **用户未指定且无列表**：先按 **`Skills/pin-management/my-requests/SKILL.md`** 执行 my-requests，得到工单列表后默认对**列表全部**生成报告（同上）。

2. **一次性调用 Jira MCP 拉取所有 PIN 的 issue 详情**
   - **Server**: `user-mcp-atlassian`
   - **Tool**: `jira_search`
   - **Arguments**：
     - `jql` = 由 PIN ID 列表拼成，例如单个 key 用 `key = "PIN-2677"`，多个 key 用 `key in (PIN-2677, PIN-2680, PIN-2681)`（列表中的 key 用逗号分隔，不要加引号）。
     - `fields` = `key,summary,status,priority,created,description`
     - `limit` = PIN 列表长度（或 50，取较小者）。
   - **一次调用**即返回所有指定 PIN 的 issue；然后对返回的**每个** issue 执行步骤 3、4、5（生成一个报告块并追加到同一 Confluence 页面）。

3. **若某 PIN 未在搜索结果中（不存在或无权限）**
   - 跳过该 key，可简短提示「PIN-xxxx 未找到或无权限」；仅对 jira_search 返回的 issue 生成报告。

4. **按模板生成 Request PIN Report**
   - 使用下方 **Output Format** 将 MCP 返回的 `summary`、`priority`、`created`、`description` 填入固定格式。
   - **需求要点**：从 `description` 中归纳为「问题、背景、业务影响、期望」四项；若 description 为一段话，按语义拆分到四项或将整段放在「需求要点」下并分条简述。

5. **读取 Confluence 目标并发布报告**
   - **Confluence 目标**：从 **`Assets/Global/profile.yaml`** 读取 **`confluence_workspace`**（Confluence 空间/文件夹 URL），作为报告发布目标；若未配置则提示用户并结束。
   - **发布规则**（无论一条还是多条，报告都发布到该 Confluence 文件夹下）：
     - **页面标题**：按报告生成日命名为「YYYY-MM-DD Processed」。
     - **同一天多批**：若该日期页面已存在，在页面**末尾**增量追加本次报告（先加分隔线再追加新报告块）；若不存在则创建新页面，内容为本次报告。多个 PIN 时，每个 PIN 一个报告块，块与块之间用分隔线隔开。
   - **对话中**：
     - **仅一条报告时**：在聊天中**直接回复**该条报告的完整正文（按 Output Format 的 Markdown），并说明「已发布到 Confluence，目标：confluence_workspace」。
     - **多条报告时**：不在对话中展示报告正文，仅简短告知「已为 N 个 PIN 生成 Report，已发布到 Confluence（confluence_workspace）」。

## 报告发布目标（Confluence）

| 项     | 说明 |
|--------|------|
| 目标来源 | **`Assets/Global/profile.yaml`** 中的 **`confluence_workspace`**（Confluence 空间/文件夹 URL） |
| 页面标题 | **`YYYY-MM-DD Processed`**（按报告生成日） |
| 新建   | 该日期页面不存在时，在 confluence_workspace 下创建新页面，内容为本次报告 |
| 追加   | 该日期页面已存在时，在页面末尾追加本次报告，用分隔线与前文区分 |
| 展示   | **仅一条**：在对话中直接回复报告正文，并说明已发布到 Confluence；**多条**：不在对话中展示正文，仅告知「已为 N 个 PIN 生成 Report，已发布到 Confluence」 |

## Output Format

报告正文（发布到 Confluence 或供粘贴）须按以下结构（Markdown）：

```markdown
# Request PIN Report — <issue_key>

**标题：** （<优先级>）<summary 原文或适度润色>

**PIN 创建时间：** <created 格式化为可读日期，如 2026-02-27>

## 需求要点

- **问题：** <从 description 归纳：客户/用户反馈的具体问题>
- **背景：** <从 description 归纳：相关上下文、时间线、已有能力等>
- **业务影响：** <从 description 归纳：对业务/团队的影响、当前替代方案等>
- **期望：** <从 description 归纳：希望产品/系统如何满足需求>
```

若 description 无法明确拆成四项，可保留整段为「需求要点」并在其下用简短分条概括；或仅填能明确对应的项，其余写「见描述」。

## MCP 与配置约定

- **Jira**：使用 **`jira_search`** 一次性按 key 拉取所有 PIN 详情。**Server**: `user-mcp-atlassian`，**工具**: `jira_search`，**参数**: `jql`（单个用 `key = "PIN-xxx"`，多个用 `key in (PIN-xxx, PIN-yyy)`）、`fields` = `key,summary,status,priority,created,description`、`limit` 按列表长度或 50。
- **Confluence 目标**：从 **`Assets/Global/profile.yaml`** 读取 **`confluence_workspace`** 作为发布目标（空间/文件夹 URL）。若 MCP 提供 Confluence 创建/更新页面能力，则在该文件夹下创建或更新标题为「YYYY-MM-DD Processed」的页面；否则将完整报告正文与 `confluence_workspace` URL 一并给出，供用户手动粘贴到该 Confluence 文件夹。

## Guardrails

- **获取 PIN ID**：由 my-requests 触发且用户未特别指定时，**默认对列表全部**工单生成报告；仅当用户**明确指定**某一或若干 PIN Key 时，才只对指定的生成。单独调用本技能且用户未指定时，先执行 my-requests 得到列表，再默认对列表全部生成。
- **报告发布与展示**：报告必须发布到 **Confluence**，目标 URL 来自 **`Assets/Global/profile.yaml`** 的 **`confluence_workspace`**；页面标题为 `YYYY-MM-DD Processed`，同一天多批则在该页面末尾追加。**仅当生成一条报告时**在对话中直接回复报告正文并说明已发布到 Confluence；**多条时**不在对话中展示正文，仅说明已发布。
- PIN Key 必须为 `PIN-` 开头的合法 issue key，且项目为 PIN（Product Intake）。
- 不捏造 description 中未出现的内容；归纳时保持与原文一致。
- 输出语言与用户一致（用户用中文则报告用中文，英文同理）；summary 可保留原文。

## Example（示例）

输入：用户指定时可为 `PIN-2677` 或「帮我把 PIN-2677 生成 Request PIN Report」；未指定时先执行 my-requests 列出未处理工单，再选一个生成报告。

报告**始终**发布到 Confluence（目标：profile 中的 `confluence_workspace`），页面标题为 `YYYY-MM-DD Processed`。**仅一条**时在对话中直接回复报告正文并说明已发布到 Confluence；**多条**时不在对话中展示正文，仅告知已发布即可。

输出结构示例：

```markdown
# Request PIN Report — PIN-2677

**标题：** （High）能否在 Target 和 Sam's Club 的跨零售商报告中加入 NTB 指标？

**PIN 创建时间：** 2026-02-27

## 需求要点

- **问题：** Campbell's 客户反馈，在报告中看不到 Target 和 Sam's Club 的 New to Brand（NTB）数据。
- **背景：** 这两个零售商在本月初已加入跨零售商报告，但 NTB 数据尚未接入，客户对之前报告上线延迟已有不满。
- **业务影响：** NTB 对该团队很重要，目前他们只能手工拉取这些数据，无法在报告中直接使用。
- **期望：** 在跨零售商报告中为 Target 和 Sam's Club 增加 NTB 指标，使客户能在报告里直接看到这两家的 NTB 数据，而不用再手动导出。
```
