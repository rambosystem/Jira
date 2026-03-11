---
name: request-pin-report
description: 根据 PIN 工单 ID 拉取 Jira 详情并生成「Request PIN Report」格式报告；多条 PIN 时逐条处理（每条单独 jira_search + 生成报告块），并用 Todo 列表跟踪进度。用户说「生成 PIN 报告」「Request PIN Report」时使用；未指定 PIN ID 时先按 my-requests 获取未处理工单列表。
---

# Request PIN Report（根据 PIN ID 生成需求报告）

## Purpose

根据 **PIN 工单 Key**（如 `PIN-2677`）调用 Jira MCP 获取 issue 详情，生成固定格式的 **Request PIN Report**（ADF Body JSON），再按 **create-page** 技能发布到 Confluence。本技能只负责「报告内容生成」；发布流程、页面标题、查找/追加等见 **`skills/confluence-management/create-page/SKILL.md`**。

## When to Use

- User asks to generate a "Request PIN Report" or "PIN 需求报告"
- User provides a PIN issue key (e.g. `PIN-2677`) and wants a structured report
- User says "根据 PIN-xxxx 生成报告" 或 "把这个 PIN 整理成需求报告"

## Input

- **PIN 工单 Key（单个或多个）**：
  - 用户**明确给出**单个或若干 PIN Key（或链接）时，仅对这些 ID 生成报告。
  - 由 **my-requests** 传入的**工单列表**（未特别指定时）：对**列表全部**生成报告，无需用户再指定；仅当用户**特别指定**某一或若干 PIN 时，才只对指定的生成。

## Workflow

**原则**：**一条 PIN 一条 PIN 处理**，禁止一次性拉取全部后再批量生成；必须用 **Todo 列表** 跟踪进度，每处理完一条 PIN 就勾选对应 todo。

1. **解析或获取 PIN ID 列表**
   - **用户已指定**：从用户输入或链接中提取一个或多个 `PIN-xxxx`，得到 PIN ID 列表。
   - **「最新 N 条」**：用 JQL 查未处理 PIN（`project = PIN AND assignee in ("<profile.me.account_id>") AND status IN ("Backlog", "Ready for Technical Review") ORDER BY created DESC`），`limit` = N，得到 issue 列表；将返回的每个 issue 的 key 组成 PIN ID 列表。
   - **由 my-requests 传入且用户未特别指定**：使用 my-requests 返回的全部工单 key 作为 PIN ID 列表。
   - **用户未指定且无列表**：先按 **`skills/pin-management/my-requests/SKILL.md`** 执行 my-requests，得到工单列表后默认对**列表全部**生成报告。

2. **创建 Todo 列表（必须）**
   - 使用 **Todo 列表**：为列表中的**每一个** PIN 创建一条 todo，例如「处理 PIN-2677：拉取详情并生成报告块」「处理 PIN-2680：拉取详情并生成报告块」。
   - 后续按 todo 顺序**逐条**执行，每完成一条 PIN 即将该 todo 标记为完成，避免一次性处理多条导致遗漏或偷懒。

3. **逐条处理每条 PIN（循环：一条 PIN 一轮）**
   对 PIN 列表中的**每一项**依次执行（不可合并为一次调用处理多条）：
   - **标记**：将当前 PIN 对应的 todo 设为 in_progress。
   - **拉取本条 PIN 的 issue 详情**：
     - **Server**: `user-mcp-atlassian`，**Tool**: `jira_search`
     - **Arguments**：`jql` = `key = "PIN-xxxx"`（当前这条的 key，不要用 `key in (...)` 一次查多条），`fields` = `key,summary,status,priority,created,description`，`limit` = 1。
   - **若未找到或无权限**：跳过该 key，简短提示「PIN-xxxx 未找到或无权限」，将对应 todo 标为完成并继续下一条。
   - **生成本条的报告块**：根据 **Report 内容结构** 与当前 issue 数据，生成**这一条 PIN** 的 ADF 报告块（blockCard → heading「需求要点」→ bulletList 四要点）。从 `description` 归纳填入；若为一段话则按语义拆分或整段简述；无法拆成四项时其余写「见描述」。将本块**追加**到已积累的 content 数组（多 PIN 时块之间可用 `rule` 分隔）。
   - **标记**：将当前 PIN 的 todo 标为 completed，再处理下一条。

4. **合并并发布**
   - 当**所有** PIN 的 todo 均完成后，将积累的 content 组装成完整 ADF 根文档 `{"version":1,"type":"doc","content":[...]}`。
   - **发布**：按 **`skills/confluence-management/create-page/SKILL.md`** 执行（**`scripts/confluence_create_page.py`**）。页面标题为报告生成日的 **`YYYY-MM-DD Processed`**。终端：`Set-Location <repo>; python scripts/...`，勿用 `&&`。
   - **对话中**：**仅一条**报告时，在聊天中回复该条报告的完整正文（按下方 Markdown 展示格式）并说明已发布；**多条**时只告知「已为 N 个 PIN 生成 Report，已发布到 Confluence」，不贴正文。

## Report 内容结构（Output Format）

本技能只定义**报告内容**的形状；发布流程与 ADF 用法见 **create-page** 技能。

每条 PIN 的报告块由三部分组成（生成 ADF 时对应节点）：

1. **URL-Card**：该 PIN 的 Jira 链接。ADF 节点：`blockCard`，`attrs.url` = `https://<site>.atlassian.net/browse/<issue_key>`。
2. **需求要点（Heading 3）**：ADF 节点 `heading`，level 3，text「需求要点」。
3. **四条要点**（bulletList）：4 个 listItem，每项为 paragraph，从 description 归纳：
   - **问题：** 客户/用户反馈的具体问题
   - **背景：** 相关上下文、时间线、已有能力等
   - **业务影响：** 对业务/团队的影响、当前替代方案等
   - **期望：** 希望产品/系统如何满足需求

多 PIN 时，多个报告块顺序拼在同一 ADF 根文档的 `content` 数组中（报告块之间可用 `rule` 分隔）。ADF 节点与结构细节见 create-page 技能的「内容格式（ADF）」；本技能不重复 Confluence API 与脚本用法。

**对话中展示示例（Markdown 等价）：**

```markdown
[URL-Card: Jira 链接 <issue_key>]

### 需求要点

- **问题：** Campbell's 客户反馈，在报告中看不到 Target 和 Sam's Club 的 New to Brand（NTB）数据。
- **背景：** 这两个零售商在本月初已加入跨零售商报告，但 NTB 数据尚未接入，客户对之前报告上线延迟已有不满。
- **业务影响：** NTB 对该团队很重要，目前他们只能手工拉取这些数据，无法在报告中直接使用。
- **期望：** 在跨零售商报告中为 Target 和 Sam's Club 增加 NTB 指标，使客户能在报告里直接看到这两家的 NTB 数据，而不用再手动导出。
```

## MCP 与配置约定

- **Jira**：**每条 PIN 单独一次** **`jira_search`**（禁止用 `key in (...)` 一次拉多条）。**Server**: `user-mcp-atlassian`，**工具**: `jira_search`，**参数**: `jql` = `key = "PIN-xxx"`（当前处理的单条）、`fields` = `key,summary,status,priority,created,description`、`limit` = 1。
- **Todo 列表**：多 PIN 时必须先建 todo（每条 PIN 一条），按顺序逐条处理并更新 todo 状态。
- **Confluence 发布**：所有 PIN 的报告块合并为一份 ADF 后，按 **`skills/confluence-management/create-page/SKILL.md`** 执行 **`scripts/confluence_create_page.py`**；页面标题为 `YYYY-MM-DD Processed`。

## Guardrails

- **逐条处理 + Todo**：多 PIN 时**必须**先建 Todo 列表（每 PIN 一条），**一条 PIN 一轮**：单次 `jira_search` 只查当前这条（`key = "PIN-xxx"`），生成该条报告块并追加到 content，再勾选 todo 继续下一条；禁止一次性 `key in (...)` 拉取多条后批量生成。
- **只生成 ADF Body JSON，不写脚本**：只根据 Jira 数据生成符合「Report 内容结构」的 ADF；禁止为构建报告编写 Python 等脚本。发布用 create-page 技能与 **`scripts/confluence_create_page.py`**。
- **获取 PIN ID**：由 my-requests 传入且用户未特别指定时，对列表**全部**工单生成报告（仍按上述逐条处理）；用户明确指定若干 PIN 时只处理指定的。
- **对话展示**：仅一条时在对话中回复报告正文并说明已发布；多条时只告知已发布、不贴正文。
- PIN Key 须为 `PIN-` 开头、项目为 PIN（Product Intake）。
- 不捏造 description 中未出现的内容；归纳与原文一致；输出语言与用户一致。
- 如果PIN超过10条，就不要在回复中列出，给出数字即可

## Example（示例）

输入：用户指定时可为 `PIN-2677` 或「帮我把 PIN-2677、PIN-2680 都生成 Request PIN Report」；未指定时先执行 my-requests 列出未处理工单。**多条时**：先建 Todo（如「处理 PIN-2677」「处理 PIN-2680」），再逐条 jira_search → 生成该条报告块 → 勾选 todo → 下一条；全部完成后合并 ADF 并发布。仅一条时在对话中回复报告正文并说明已发布，多条时只告知已发布。

报告正文结构示例（URL-Card + 需求要点 + 四条要点）：

```markdown
[URL-Card: Jira 链接 PIN-2677]

### 需求要点

- **问题：** Campbell's 客户反馈，在报告中看不到 Target 和 Sam's Club 的 New to Brand（NTB）数据。
- **背景：** 这两个零售商在本月初已加入跨零售商报告，但 NTB 数据尚未接入，客户对之前报告上线延迟已有不满。
- **业务影响：** NTB 对该团队很重要，目前他们只能手工拉取这些数据，无法在报告中直接使用。
- **期望：** 在跨零售商报告中为 Target 和 Sam's Club 增加 NTB 指标，使客户能在报告里直接看到这两家的 NTB 数据，而不用再手动导出。
```
