---
name: create-page
description: 在 profile 配置的 Confluence 文件夹下创建或更新页面。按标题查找已有页面，存在则追加/覆盖内容，不存在则新建。被 request-pin-report 等技能用于发布报告；用户说「发布到 Confluence」「创建 Confluence 页面」时也可直接使用。
---

# Create Confluence Page（创建/更新 Confluence 页面）

## Purpose

在 **Confluence** 的指定空间、指定父页面（文件夹）下，按**页面标题**创建新页面或更新已有页面。目标空间与父文件夹来自 **`Assets/Global/profile.yaml`** 的 **`confluence_workspace`**（Confluence 空间/文件夹 URL）。

## When to Use

- 其他技能需要将内容发布到 Confluence（如 **request-pin-report** 发布 PIN 报告到「YYYY-MM-DD Processed」页面）
- 用户说「发布到 Confluence」「把内容发到 Confluence」「创建 Confluence 页面」

## Configuration to Read

- **`Assets/Global/profile.yaml`**：读取 **`confluence_workspace`**（Confluence 文件夹 URL）。
  - URL 形如：`https://<site>.atlassian.net/wiki/spaces/<space_key>/folder/<parent_id>?...`
  - 从中解析：
    - **space_key**：`/spaces/` 后、`/folder/` 前的路径段（如个人空间 `~71202095adf17bc3ec4b54a0572777a6a9cab2`）
    - **parent_id**：`/folder/` 后的数字 ID（如 `1263042720`）
  - 若未配置 `confluence_workspace` 或无法解析，则提示用户并结束。

## Workflow

1. **解析 Confluence 目标**
   - 读取 **`Jira/Assets/Global/profile.yaml`** 中的 **`confluence_workspace`**。
   - 从 URL 提取 **space_key** 与 **parent_id**（见上）。若 profile 中已单独配置 `confluence_space_key` / `confluence_parent_id` 则优先使用。

2. **检查页面是否已存在**
   - **Server**: `user-mcp-atlassian` · **Tool**: `confluence_get_page`
   - **Arguments**: `title` = 目标页面标题（如 `2026-03-11 Processed`）；`space_key` = 上步得到的 space_key；`include_metadata` = true。
   - 若返回错误或「not found」，则视为页面不存在，进入步骤 4（创建）；否则进入步骤 3（更新）。

3. **更新已有页面**
   - 从 `confluence_get_page` 的返回中取得 **page_id** 及当前 **content**（若为 Markdown 则可直接拼接）。
   - **追加模式**（如 PIN 报告同一天多批）：新内容 = 当前 content + 分隔线 + 本次要发布的内容。
   - **覆盖模式**（调用方指定）：新内容 = 本次要发布的内容。
   - **Server**: `user-mcp-atlassian` · **Tool**: `confluence_update_page`
   - **Arguments**: `page_id`、`title`（保持不变）、`content` = 新内容；`content_format` = `markdown`（默认）。

4. **创建新页面**
   - **Server**: `user-mcp-atlassian` · **Tool**: `confluence_create_page`
   - **Arguments**: `space_key`、`title`、`content` = 本次要发布的内容；`parent_id` = 上步得到的 parent_id；`content_format` = `markdown`（默认）。

5. **返回结果**
   - 返回创建/更新后的页面 URL 或 page_id，并简短告知「已发布到 Confluence，目标：confluence_workspace」。

## Input（由调用方或用户提供）

| 参数        | 说明                                                          |
| ----------- | ------------------------------------------------------------- |
| **title**   | 页面标题（必填），如 `2026-03-11 Processed`                   |
| **content** | 页面正文，Markdown 字符串（必填）                             |
| **append**  | 可选，是否在已有页面末尾追加（默认 true）；false 表示覆盖整页 |

## Output

- 成功：返回 Confluence 页面 URL，并说明已发布到 profile 中的 confluence_workspace。
- 失败：提示「未配置 confluence_workspace」或 MCP 报错信息。

## MCP 工具（快捷参考）

- **confluence_get_page**：按 `title` + `space_key` 查询页面，获取 page_id 与当前 content。
- **confluence_create_page**：必填 `space_key`, `title`, `content`；可选 `parent_id`, `content_format`（默认 markdown）。
- **confluence_update_page**：必填 `page_id`, `title`, `content`；可选 `content_format`（默认 markdown）。

详见 **`Skills/confluence-management/MCP-tools.md`**。

## Guardrails

- 必须先读取 profile 中的 `confluence_workspace` 并解析出 space_key、parent_id；未配置则不能调用 MCP 创建/更新。
- 更新时保留原 content 再追加或按约定覆盖，避免误删已有内容。
- 所有 Confluence 调用均使用 **Server**: `user-mcp-atlassian`。
