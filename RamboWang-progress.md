# Progress

## 2026-03-11 — 50 条未处理 PIN 查询与报告发布

- **查询**：JQL `project = PIN AND assignee = me AND status IN (Backlog, Ready for Technical Review)`，limit 50，得到 50 条工单。
- **报告**：按 request-pin-report 流程逐条 jira_search 拉取 description，生成 50 个 Request PIN Report 块（blockCard + 需求要点 + 四要点），合并为 ADF 写入 `report_adf.json`。
- **发布**：`confluence_create_page.py --title "2026-03-11 Processed" --body-file report_adf.json`，新建 Confluence 页面并发布。

## 2026-03-11 — request-pin-report 逐条处理 + Todo

- **SKILL 优化**：多条 PIN 时改为**一条 PIN 一条 PIN 处理**，避免一次性拉取/生成过多导致遗漏或偷懒。
- **强制 Todo 列表**：先为每个 PIN 建一条 todo（如「处理 PIN-xxx：拉取详情并生成报告块」），按顺序逐条执行并更新 todo 状态。
- **每轮单条**：每轮只对**当前** PIN 调用一次 `jira_search`（`key = "PIN-xxx"`，禁止 `key in (...)`），生成该条报告块并追加到 content，勾选 todo 后再处理下一条；全部完成后合并 ADF、一次发布到 Confluence。

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
