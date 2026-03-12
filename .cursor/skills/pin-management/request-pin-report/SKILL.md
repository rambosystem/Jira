---
name: request-pin-report
description: 根据 PIN 工单生成「Request PIN Report」ADF JSON，可发布到 Confluence。用户说「生成 PIN 报告」「Request PIN Report」「按 PIN 生成 Confluence 报告」时使用。
---

# Request PIN Report

## Purpose

- 确定要处理的 PIN ID 列表（用户指定 / 最新 N 条 / my-requests 列表）
- 调用 `scripts/pin/request_pin_report_json.py` 生成 ADF JSON（含 LLM 并发分析）
- 用 create-page 技能发布到 Confluence

## Workflow

1. **确定 PIN ID**：用户给的 ID、或「最新 N 条」用 `--latest N`、或 my-requests 列表拼成 `--pin-ids`。
2. **生成 JSON**（输出到 repo 下 `tmp/`，仅覆盖不删除）。`--output` / `--analysis-output` 为相对于 `tmp/` 的文件名，不要加 `tmp/` 前缀：

```bash
python scripts/pin/request_pin_report_json.py --pin-ids "PIN-2677,PIN-2680" --output pin_report_adf.json --analysis-output pin_analysis.json
# 或：--latest 5 --output pin_report_adf.json --analysis-output pin_analysis.json
```

3. **发布**：用 create-page，body 来自 `tmp/`。`--body-file` 为相对于 `tmp/` 的文件名（如 `pin_report_adf.json`，不要写 `tmp/pin_report_adf.json`）。标题格式为 **`Request PIN Report YYYY-MM-DD`**（如 `Request PIN Report 2026-03-12`）。**默认**会从 body 中识别 PIN（blockCard URL），发布后删除这些 PIN 与本页的 remotelink；不需再传 `--unlink-issues`。若不要删除关联则加 `--no-unlink`：

```bash
python scripts/confluence/confluence_create_page.py --title "Request PIN Report 2026-03-12" --body-file pin_report_adf.json
# 不解除 PIN 与本页关联：加 --no-unlink
```

## tmp/ 状态（防止用错页面 ID）

- **生成**：`scripts/pin/request_pin_report_json.py` 写入 `tmp/pin_report_adf.json`、`tmp/pin_analysis.json`。
- **发布**：`scripts/confluence/confluence_create_page.py` 从 `tmp/` 读 body，发布后**写入** `tmp/confluence_page_latest.json`（含 `page_id`、`url`、`title`），后续解除关联一律使用该文件中的 `page_id`，避免幻觉或手填 ID。
- **再解除**：使用 `scripts/pin/unlink_pins_from_latest_page.py`，自动读 `tmp/confluence_page_latest.json`（页面 ID）和 `tmp/pin_analysis.json`（PIN 列表），无需传页面 ID。

```bash
python scripts/pin/unlink_pins_from_latest_page.py
```

## 约定

- 脚本：`scripts/pin/request_pin_report_json.py`（`--pin-ids` 或 `--latest`）→ 一次 Jira 查询 + 并发 LLM → 写入 `tmp/`；`scripts/confluence/confluence_create_page.py` 从 `tmp/` 读 body，发布后写入 `tmp/confluence_page_latest.json`。
- 输出：ADF doc，每 PIN 一块 blockCard + 需求要点（问题 / 背景 / 业务影响 / 期望），多 PIN 用空行分隔。
- 描述归纳忠于 Jira，不杜撰；PIN key 为 `PIN-<number>`。
