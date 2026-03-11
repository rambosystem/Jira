---
name: create-page
description: 在 profile 配置的 Confluence 文件夹下创建或更新页面。按标题查找已有页面，存在则追加/覆盖内容，不存在则新建。使用 Confluence REST API v2，不依赖 MCP。被 request-pin-report 等技能用于发布报告；用户说「发布到 Confluence」「创建 Confluence 页面」时也可直接使用。
---

# Create Confluence Page（创建/更新 Confluence 页面）

## Purpose

在 **Confluence** 的指定空间、指定父页面（文件夹）下，按**页面标题**创建新页面或更新已有页面。目标空间与父文件夹来自 **`Assets/Global/profile.yaml`** 的 **`confluence_workspace`**。本技能使用 **Confluence Cloud REST API v2** 直接调用，不依赖 MCP。

## When to Use

- 其他技能需要将内容发布到 Confluence（如 **request-pin-report** 发布 PIN 报告到「YYYY-MM-DD Processed」页面）
- 用户说「发布到 Confluence」「把内容发到 Confluence」「创建 Confluence 页面」

## Configuration to Read

- **`Assets/Global/profile.yaml`**：从以下**固化字段**读取 Confluence 目标，无需解析 URL 或调用 GET /spaces：
  - **confluence_base_url**：站点根，如 `https://pacvue-enterprise.atlassian.net`
  - **confluence_space_key**：空间 key，如 `~71202095adf17bc3ec4b54a0572777a6a9cab2`
  - **confluence_parent_id**：父页面/文件夹数字 ID，如 `1263042720`
  - **confluence_space_id**：数字 **spaceId**（v2 API 创建/查询页面用），如 `32113549`
  - 可选保留 **confluence_workspace** 作为完整文件夹 URL 参考。
  - 若上述任一未配置，则提示用户并结束。

## Authentication

- **方式**：HTTP Basic Auth。
- **用户名**：Confluence 账户邮箱（可从 profile 的 `me.email` 或环境变量 `CONFLUENCE_EMAIL` 获取）。
- **密码**：Atlassian API Token（从环境变量 `CONFLUENCE_API_TOKEN` 或调用方提供的凭证获取；**勿在代码中硬编码**）。
- **Header**：`Authorization: Basic <Base64(email:api_token)>`，`Accept: application/json`，`Content-Type: application/json`。

## REST API v2 流程

Base path：`{base_url}/wiki/api/v2`（例如 `https://pacvue-enterprise.atlassian.net/wiki/api/v2`）。

### 1. 读取 Confluence 目标（profile 固化）

- 从 **`Assets/Global/profile.yaml`** 读取：**confluence_base_url**、**confluence_space_id**（数字）、**confluence_parent_id**（可选保留 **confluence_space_key** 用于展示）。无需解析 URL，无需调用 GET /spaces。

### 2. 检查页面是否已存在（推荐先查再决定创建/更新）

- **请求**：`GET /pages?space-id={confluence_space_id}&title={urlEncodedTitle}&limit=1`
- **说明**：按空间 + 标题查询；标题需 URL 编码。**confluence_space_id** 来自 profile。
- **若** 返回 `results` 非空：取 `results[0].id` 为 **page_id**，进入步骤 4（更新/追加）。
- **若** 无结果或报错：视为页面不存在，进入步骤 3（创建）。
- **执行方式**：页面创建/更新**一律**通过 **`scripts/confluence_create_page.py`** 执行。调用方（如 request-pin-report）**只生成 ADF Body JSON**（不为此编写 Python 或其他脚本），通过 `--body-file`（或 `--body-json`、`--jira-url`）传入；脚本已实现「先按标题查找 → 存在则 GET 并合并 ADF 后 PUT，否则 POST」。

### 3. 创建新页面

- **请求**：`POST /pages`
- **Body（application/json）**：
  - `spaceId`（string，必填）：profile 中的 **confluence_space_id**
  - `parentId`（string，可选）：profile 中的 **confluence_parent_id**
  - `title`（string，必填）：页面标题
  - `status`（string，可选）：`"current"` 表示已发布
  - `body`（object，必填）：
    - **Markdown 正文**：可转为 ADF 或 storage。推荐 **atlas_doc_format**：
      - `body.representation = "atlas_doc_format"`
      - `body.value` = ADF 根文档 JSON 字符串（见下方「内容格式」）
    - **或** 使用 `representation: "storage"`、`value` 为 Confluence 存储格式（XHTML）的字符串
- **响应**：`id`、`_links.webui`；拼接 base_url + `_links.webui` 即页面 URL。

### 4. 更新已有页面

- **请求**：`GET /pages/{page_id}`（可选，若需当前 body/version）
- **请求**：`PUT /pages/{page_id}`
- **Body**：需包含 `version.number`（当前版本号 + 1，用于乐观锁）；`body` 同创建时的结构（`representation` + `value`）。
- **追加模式**（如 PIN 报告同一天多批）：先 GET 该页获取当前 body，将当前内容与本次内容合并后再写入 `body.value`。
- **覆盖模式**：直接 `body.value` = 本次要发布的内容。

### 5. 返回结果

- 返回创建/更新后的页面 URL（`base_url + _links.webui`）或 page_id，并简短告知「已发布到 Confluence，目标：confluence_workspace」。

## 内容格式（ADF）

REST API v2 的 body 使用 **atlas_doc_format** 时，`body.value` 为 ADF 根文档的 **JSON 字符串**。结构示例：

```json
{
  "version": 1,
  "type": "doc",
  "content": [
    {
      "type": "paragraph",
      "content": [{ "type": "text", "text": "段落文字" }]
    },
    {
      "type": "blockCard",
      "attrs": { "url": "https://site.atlassian.net/browse/PROJ-123" }
    }
  ]
}
```

- **纯文本/Markdown**：可转换为 ADF 的 `paragraph`、`heading` 等节点（多段即多个 `paragraph`）。
- **Jira 链接卡片**：使用节点 `type: "blockCard"`，`attrs.url` 为 Jira issue 的 browse URL。
- 若调用方提供的是 Markdown 字符串，执行方需将其转为上述 ADF 再赋给 `body.value`。

## Input（由调用方或用户提供）

| 参数        | 说明                                                          |
| ----------- | ------------------------------------------------------------- |
| **title**   | 页面标题（必填），如 `2026-03-11 Processed`                   |
| **content** | 页面正文：Markdown 字符串或已构建的 ADF JSON 字符串（必填）   |
| **append**  | 可选，是否在已有页面末尾追加（默认 true）；false 表示覆盖整页 |

## Output

- **成功**：返回 Confluence 页面 URL，并说明已发布到 profile 中的 confluence_workspace。
- **失败**：提示「未配置 confluence_workspace」或 REST API 返回的状态码与错误体。

## 参考

- **Confluence Cloud REST API v2**：<https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/>
  - Create page: `POST /wiki/api/v2/pages`
  - Update page: `PUT /wiki/api/v2/pages/{id}`
  - Get pages: `GET /wiki/api/v2/pages?space-id=...&title=...`
  - **spaceId / parentId**：从 profile 的 **confluence_space_id**、**confluence_parent_id** 读取，无需再调 GET /spaces。
- **本仓库脚本**：`scripts/confluence_create_page.py`。从 profile 读 confluence_*；认证用 `CONFLUENCE_EMAIL`、`CONFLUENCE_API_TOKEN`。支持 `--title`、`--body-file`、`--body-json`、`--jira-url`；按标题先查页，存在则追加、否则新建。

### 执行脚本（终端）

- **工作目录**：须在仓库根目录执行（脚本会读 `Assets/Global/profile.yaml` 与相对路径的 `--body-file`）。
- **Windows PowerShell**：不要使用 `cd /d ... && python ...`，因 **`&&` 在 PowerShell 5.x 中不是有效语句分隔符**。请用以下任一方式：
  - 分号连接：`Set-Location <仓库根路径>; python scripts/confluence_create_page.py --title "2026-03-11 Processed" --body-file report.json`
  - 或先切换目录再执行：先 `Set-Location <仓库根路径>`，再单独运行 `python scripts/confluence_create_page.py ...`。
- **示例（PowerShell）**：`Set-Location e:\Workspace\Jira; python scripts/confluence_create_page.py --title "2026-03-11 Processed" --body-file report.json`

## Guardrails

- **一律使用脚本**：Confluence 页面的创建/更新**必须**通过 **`scripts/confluence_create_page.py`** 执行；调用方只提供 ADF 正文（如写入临时 JSON 后 `--body-file`），**禁止**为发布 Confluence 页面而编写新的 Python 或其他脚本。
- **终端调用**：在 Windows PowerShell 中执行脚本时，使用 `Set-Location <repo>; python scripts/...` 或先 cd 再执行，**不要使用** `cd /d ... && python ...`（`&&` 在 PowerShell 5.x 中无效）。
- 必须从 profile 读取 **confluence_base_url**、**confluence_space_id**、**confluence_parent_id**；任一未配置则不能调用 API。
- 更新时保留原 content 再追加或按约定覆盖，避免误删已有内容；PUT 时需带正确的 `version.number`。
- 认证信息使用环境变量或 profile，不在代码中硬编码 API token。
