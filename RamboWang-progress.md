# Progress

## 2026-03-11 — 整体流程优化

- **confluence_create_page.py 重构**
  - 流程改为「先按标题查找页面 → 存在则 GET body、合并 ADF、PUT 追加；不存在则 POST 新建」。不再依赖 400 报错再重试。
  - 抽取 `api_request`、`find_page_by_title`、`get_page_body`、`merge_adf_content`、`build_adf_from_args`，减少重复代码。
  - 支持 `--body-file` 传入 ADF JSON 文件路径，便于长内容发布。
- **request-pin-report 技能**
  - 明确「最新 N 条未处理 PIN」流程：直接用 JQL（assignee + status IN + ORDER BY created DESC）+ limit=N 一次 jira_search 拉取带 description 的 issue，无需先跑 my-requests。
  - 发布说明更新：脚本已实现查标题后追加/新建，一次调用即可；推荐 `--body-file`。
- **create-page 技能**：步骤 2 补充「脚本已实现先查再创建/更新」；参考处更新为 scripts 路径与 `--body-file` 示例。

## 2026-03-11 — Confluence ADF blockCard 创建脚本（历史）

- **实现**: `scripts/confluence_create_page.py`（Python）；profile 固化 confluence_*；先查后建/追加。
- **认证**: CONFLUENCE_EMAIL + CONFLUENCE_API_TOKEN（环境变量或 .env）。
