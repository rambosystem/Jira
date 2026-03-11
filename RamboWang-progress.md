# Progress

## 2026-03-11 — Confluence ADF blockCard 创建脚本

- **目标**: 使用 Confluence REST API v2 在 profile 配置的文件夹下创建包含 ADF blockCard（Jira 链接）的页面。
- **实现**: `scripts/confluence-create-adf-page.ps1`
  - 从 profile `confluence_workspace` 解析 space key、parentId（文件夹 1263042720）。
  - 调用 `GET /wiki/api/v2/spaces?keys=<key>` 解析出数字 `spaceId`（v2 创建页面需要）。
  - `POST /wiki/api/v2/pages`，body 使用 `representation: "atlas_doc_format"`，`value` 为 ADF JSON（根 `doc` + 子节点 `blockCard`，`attrs.url` 为 Jira browse URL）。
- **认证**: Basic Auth = email + API token；支持环境变量 `CONFLUENCE_API_TOKEN`、`CONFLUENCE_EMAIL`，否则需在脚本中填写（勿提交真实 token）。
- **测试结果**: 成功创建页面，返回 URL（示例）：`https://pacvue-enterprise.atlassian.net/spaces/~71202095adf17bc3ec4b54a0572777a6a9cab2/pages/1261764827/ADF+blockCard+Test+...`
