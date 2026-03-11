---
name: request-pin-report
description: 根据 PIN 工单 ID 拉取 Jira 详情并生成「Request PIN Report」格式报告。用户说「生成 PIN 报告」「Request PIN Report」时使用；通常用户不会给链接，未指定 PIN ID 时先按 my-requests 获取其未处理工单列表再确定目标工单。
---

# Request PIN Report（根据 PIN ID 生成需求报告）

## Purpose

根据 **PIN 工单 Key**（如 `PIN-2677`）调用 Jira MCP 获取 issue 详情，生成固定格式的 **Request PIN Report** 并**仅写入文件**，不在对话中展示报告正文。

## When to Use

- User asks to generate a "Request PIN Report" or "PIN 需求报告"
- User provides a PIN issue key (e.g. `PIN-2677`) and wants a structured report
- User says "根据 PIN-xxxx 生成报告" 或 "把这个 PIN 整理成需求报告"

## Input

- **PIN 工单 Key**：用户**未指定**时，不主动索要链接；通过 **my-requests** 获取工单列表后再确定。仅当用户**明确给出** PIN Key（如 `PIN-2677`）或链接（如 `.../browse/PIN-2677`）时，直接使用该 ID。

## Workflow

1. **解析或获取 PIN ID**
   - **用户已指定**：从用户输入或链接中提取 `PIN-xxxx`（如 `PIN-2677`），直接进入步骤 2。
   - **用户未指定**：先按 **`Skills/pin-management/my-requests/SKILL.md`** 执行 my-requests 工作流，获取当前用户未处理的 PIN 工单列表（按状态分组展示）；再请用户从列表中指定要生成报告的工单 Key，或按约定取列表中某一项（如第一条），得到 PIN ID 后进入步骤 2。

2. **调用 Jira MCP 获取 issue**
   - **Server**: `user-mcp-atlassian`
   - **Tool**: `jira_get_issue`
   - **Arguments**: `issue_key` = 解析得到的 PIN Key（如 `"PIN-2677"`）。
   - 可选：`fields` 不传则使用默认字段（通常已含 summary, description, status, priority, created 等）。

3. **若 issue 不存在或无权限**
   - 提示用户「未找到该 PIN 工单或当前无权限访问」，并结束。

4. **按模板生成 Request PIN Report**
   - 使用下方 **Output Format** 将 MCP 返回的 `summary`、`priority`、`created`、`description` 填入固定格式。
   - **需求要点**：从 `description` 中归纳为「问题、背景、业务影响、期望」四项；若 description 为一段话，按语义拆分到四项或将整段放在「需求要点」下并分条简述。

5. **持久化到 Workspace（不展示正文）**
   - **路径**：工作区根目录下的 `Workspace` 文件夹；若不存在则创建该目录。
   - **文件名**：`YYYY-MM-DD-Processed.md`（按**当前日期**，即报告生成日）。
   - **写入规则**：
     - 若该日期文件**不存在**：创建 `Workspace/YYYY-MM-DD-Processed.md`，内容为本次生成的报告（可含一级标题如「# YYYY-MM-DD Processed」再接报告正文）。
     - 若该日期文件**已存在**：在文件**末尾**增量追加本次报告（先加分隔线如 `---` 或 `## ---` 再追加新报告块），不覆盖原有内容。
   - **对话中**：不粘贴报告正文，仅简短告知「已生成 Report，路径：Workspace/YYYY-MM-DD-Processed.md」。

## 报告输出路径（持久化）

| 项     | 说明 |
|--------|------|
| 目录   | 工作区根目录下的 **`Workspace`**（不存在则创建） |
| 文件名 | **`YYYY-MM-DD-Processed.md`**（按报告生成日） |
| 新建   | 文件不存在时创建，内容为本次报告 |
| 追加   | 文件已存在时在文件末尾追加本次报告，用分隔线与前文区分 |
| 展示   | **不在对话中展示**报告正文；完成后仅简短告知「已生成 Report，路径：Workspace/YYYY-MM-DD-Processed.md」即可 |

## Output Format

写入文件时，报告正文须按以下结构（Markdown）：

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

## MCP 调用约定

- 仅使用 **`jira_get_issue`**，无需读 mcps 下 descriptor。
- **Server**: `user-mcp-atlassian`  
- **必填参数**: `issue_key`（字符串，如 `"PIN-2677"`）。

## Guardrails

- **获取 PIN ID**：用户未指定工单时，必须通过 **my-requests** 技能获取工单列表并据此确定目标；不假设用户会提供链接。
- **报告持久化**：报告必须写入 `Workspace/YYYY-MM-DD-Processed.md`（工作区根目录即当前仓库根）；若 `Workspace` 目录不存在则先创建再写文件；追加时仅在末尾追加，不覆盖已有内容。**不在对话中展示报告正文**，仅写文件并简短确认路径。
- PIN Key 必须为 `PIN-` 开头的合法 issue key，且项目为 PIN（Product Intake）。
- 不捏造 description 中未出现的内容；归纳时保持与原文一致。
- 输出语言与用户一致（用户用中文则报告用中文，英文同理）；summary 可保留原文。

## Example（示例）

输入：用户指定时可为 `PIN-2677` 或「帮我把 PIN-2677 生成 Request PIN Report」；未指定时先执行 my-requests 列出未处理工单，再选一个生成报告。

报告**仅**写入或追加到 `Workspace/YYYY-MM-DD-Processed.md`，**不在对话中展示**报告正文；完成后可简短告知用户已生成及文件路径即可。

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
