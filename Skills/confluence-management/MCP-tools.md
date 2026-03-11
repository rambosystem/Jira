# MCP 工具链（confluence-management）

在 Confluence 空间下创建、更新、查询页面及附件/评论时用到的 Atlassian MCP 工具。**Server** 均为 `user-mcp-atlassian`。实际工具名以当前启用的 MCP server 提供的为准。

## 页面创建与更新（create-page 技能核心）

| 流程环节         | 用途                          | MCP 工具                 | 说明                                                                                       |
| ---------------- | ----------------------------- | ------------------------ | ------------------------------------------------------------------------------------------ |
| 检查页面是否存在 | 按标题 + 空间查询是否已有页面 | `confluence_get_page`    | 入参：`title` + `space_key`；返回 page_id、content、metadata，用于决定创建或更新           |
| 创建页面         | 在指定空间/父页面下新建页面   | `confluence_create_page` | 入参：`space_key`, `title`, `content`；可选 `parent_id`, `content_format`（默认 markdown） |
| 更新页面         | 修改已有页面标题与正文        | `confluence_update_page` | 入参：`page_id`, `title`, `content`；可选 `content_format`, `version_comment`              |

## 快捷参数（免读 schema）

**Server** 均为 `user-mcp-atlassian`。

| 工具                       | 必填参数                                       | 可选参数                                                                                                                |
| -------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **confluence_get_page**    | 二选一：`page_id` **或** `title` + `space_key` | `include_metadata`（默认 true）, `convert_to_markdown`（默认 true）                                                     |
| **confluence_create_page** | `space_key`, `title`, `content`                | `parent_id`, `content_format`（默认 `markdown`）, `enable_heading_anchors`, `emoji`                                     |
| **confluence_update_page** | `page_id`, `title`, `content`                  | `content_format`（默认 `markdown`）, `is_minor_edit`, `version_comment`, `parent_id`, `enable_heading_anchors`, `emoji` |

## 其他 Confluence 工具（按需使用）

| 工具                                                                             | 用途                                                                                            |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **confluence_search**                                                            | 按关键词或 CQL 搜索页面；入参：`query`（简单文本或 CQL），可选 `limit`（1–50）, `spaces_filter` |
| **confluence_get_page_children**                                                 | 获取某页面的子页面列表                                                                          |
| **confluence_get_page_history**                                                  | 获取页面版本历史                                                                                |
| **confluence_get_page_diff**                                                     | 获取页面版本差异                                                                                |
| **confluence_move_page**                                                         | 移动页面到新父页面                                                                              |
| **confluence_delete_page**                                                       | 删除页面                                                                                        |
| **confluence_add_comment**                                                       | 在页面上添加评论                                                                                |
| **confluence_get_comments**                                                      | 获取页面评论                                                                                    |
| **confluence_reply_to_comment**                                                  | 回复评论                                                                                        |
| **confluence_add_label**                                                         | 为页面添加标签                                                                                  |
| **confluence_get_labels**                                                        | 获取页面标签                                                                                    |
| **confluence_get_page_views**                                                    | 获取页面浏览信息                                                                                |
| **confluence_upload_attachment** / **confluence_upload_attachments**             | 上传附件                                                                                        |
| **confluence_get_attachments**                                                   | 获取页面附件列表                                                                                |
| **confluence_download_attachment** / **confluence_download_content_attachments** | 下载附件                                                                                        |
| **confluence_delete_attachment**                                                 | 删除附件                                                                                        |
| **confluence_get_page_images**                                                   | 获取页面中的图片                                                                                |
| **confluence_search_user**                                                       | 搜索 Confluence 用户                                                                            |

## 配置约定

- **发布目标**：从 **`Assets/Global/profile.yaml`** 的 **`confluence_workspace`** 读取 Confluence 文件夹 URL。
- **URL 解析**：URL 形如 `.../spaces/<space_key>/folder/<parent_id>?...`，从中提取 `space_key` 与 `parent_id` 供 `confluence_create_page`（parent_id）、`confluence_get_page`（space_key）使用。
- **内容格式**：默认使用 `content_format: "markdown"`，正文以 Markdown 传入即可。

## 调用约定

- **create-page 技能**：先 `confluence_get_page(title, space_key)` 判断是否存在；存在则 `confluence_update_page`（可追加 content），不存在则 `confluence_create_page(space_key, title, content, parent_id)`。
- 所有 Confluence 写操作（创建、更新、删除、移动、评论、附件）均需 MCP 未处于只读模式。
