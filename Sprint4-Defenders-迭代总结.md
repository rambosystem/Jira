# Sprint4 Defenders 迭代总结（26Q1-Sprint4-Defenders）

已完成 Story 共 **20 条**，按功能模块汇总如下。

---

## 1. My Report

| Key      | 内容                                                                      |
| -------- | ------------------------------------------------------------------------- |
| CP-34908 | Criteo / Target / Doordash / Kroger - Keyword Report 支持 Keyword ID 字段 |
| CP-43662 | Send to SFTP 支持公钥/私钥认证（Public & Private Key Authorization）      |
| CP-44055 | Doordash - 新增客户指标与 Ad SKU Sales 指标                               |
| CP-45668 | My Report - TikTok EU 测试                                                |

**迭代要点**：多平台 Keyword Report 增强、SFTP 认证方式扩展、Doordash 指标扩展、TikTok EU 场景验证。

---

## 2. Dayparting Scheduler

| Key      | 内容                                       |
| -------- | ------------------------------------------ |
| CP-42058 | L'Oreal Benelux - Bol Dayparting Scheduler |
| CP-43669 | Kroger - New Version Support（新版本支持） |
| CP-44210 | Reddit - Scheduler Setting 交互优化        |

**迭代要点**：Benelux/Bol 场景落地、Kroger 新版本支持、Reddit 时段设置交互优化。

---

## 3. Budget Scheduler

| Key      | 内容                                       |
| -------- | ------------------------------------------ |
| CP-43670 | Kroger - New Version Support（新版本支持） |

**迭代要点**：Kroger 预算调度新版本支持，与 Dayparting 协同。

---

## 4. SOV

| Key      | 内容                                                 |
| -------- | ---------------------------------------------------- |
| CP-44153 | Walmart - MX Market（墨西哥市场）                    |
| CP-44573 | [Crawl Task] Walmart - MX Market                     |
| CP-44646 | All Platforms - Keyword Tag 重命名为 SOV Keyword Tag |

**迭代要点**：Walmart 墨西哥市场支持（含爬虫任务）、全平台 SOV Keyword Tag 命名统一。

---

## 5. Calendar Center

| Key      | 内容                                  |
| -------- | ------------------------------------- |
| CP-44578 | Target - Event Management（活动管理） |
| CP-44579 | Target - Enable / Pause Lineitem      |
| CP-44580 | Target - Enable / Pause ASIN          |
| CP-44581 | Target - Snapshot（快照）             |

**迭代要点**：Target 日历中心能力闭环：活动管理、Lineitem/ASIN 启用与暂停、快照能力。

---

## 6. Creative Management（Creative Hub）

| Key      | 内容                                                  |
| -------- | ----------------------------------------------------- |
| CP-44930 | 同步历史补偿机制                                      |
| CP-45415 | 补全 Creative Hub 遗漏埋点（以 Excel 为准并完成检查） |

**迭代要点**：历史数据同步补偿、埋点补齐与校验，支撑数据与分析准确性。

---

## 7. 自动化 / 调度（Automation Priority）

| Key      | 内容                                       |
| -------- | ------------------------------------------ |
| CP-44731 | Kroger - New Version Support（新版本支持） |

**迭代要点**：Kroger 自动化优先级新版本支持，与 Budget/Dayparting 的 Kroger 能力对齐。

---

## 汇总

| 模块                 | 完成 Story 数 | 主要方向                                        |
| -------------------- | ------------- | ----------------------------------------------- |
| My Report            | 4             | 多平台报表、SFTP 认证、Doordash 指标、TikTok EU |
| Dayparting Scheduler | 3             | Benelux/Bol、Kroger 新版本、Reddit 交互         |
| Budget Scheduler     | 1             | Kroger 新版本                                   |
| SOV                  | 3             | Walmart MX、SOV Keyword Tag 统一                |
| Calendar Center      | 4             | Target 活动管理、启停控制、快照                 |
| Creative Management  | 2             | 同步补偿、埋点补全                              |
| Automation Priority  | 1             | Kroger 新版本                                   |
| **合计**             | **20**        | —                                               |

---

_数据来源：Jira CP 项目，Sprint = 26Q1-Sprint4-Defenders，statusCategory = Done。_

#### Budget Manager V3.29

For Amazon：

- Update: Allow users to save the filter
- Update: Add a notification when the client saves 0 budget in BM

For Reddit:

- New: Rollout Budget Manager to Reddit

Click [here](https://pacvue-enterprise.atlassian.net/wiki/x/zIJMSg) for more details.
