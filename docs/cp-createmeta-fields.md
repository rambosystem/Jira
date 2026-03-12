# CP 项目创建工单字段（Create Metadata）

由 `scripts/jira/get_createmeta.py CP` 从 Jira API 拉取。

## Issue 类型与 ID

| 类型 | id | 说明 |
|------|-----|------|
| Epic | 10000 | |
| Story | 10004 | |
| Bug | 10011 | |
| Sub-task | 10016 | |
| Technical Story | 10528 | |
| Dev Bug（已废弃，请勿创建） | 10529 | 废弃 |
| Dev Bug (Sub-task) | 11224 | |
| UX Defect (Sub-task) | 11291 | |

---

## Epic (10000)

**必填**: Components, Delivery Quarter (customfield_12899), issuetype, Priority, project, Summary  
**可选**: Assignee, Epic Name (customfield_10011), Epic Link (customfield_10014), Sprint (customfield_10020), Story Points (customfield_10033), Feature Tier (customfield_10244), CapEx (customfield_12764), Description, Due date, Fix versions, Labels, Parent

---

## Story (10004)

**必填**: Components, Client ID (customfield_10043), Story Type (customfield_10085), UX Review Required? (customfield_13319), issuetype, Priority, project, Summary  
**可选**: Assignee, Epic Link (customfield_10014), Sprint (customfield_10020), Story Points (customfield_10033), Feature Tier (customfield_10244), Last Response Date (customfield_10545), UX Review Status (customfield_13320), Description, Due date, Fix versions, Labels, Parent

---

## Bug (10011)

**必填**: Components, Client ID (customfield_10043), Severity (customfield_10054), Bug Source (customfield_12730), issuetype, Priority, project, Summary  
**可选**: Assignee, Epic Link, Sprint, Tier (customfield_10047), Fixer (customfield_10053), Cause Category (customfield_10055), Description, Due date, Fix versions, Labels, Parent, Time tracking, Affects versions

---

## Sub-task (10016)

**必填**: issuetype, **Parent**, Priority, project, Summary  
**可选**: Assignee, Components, Sprint, Start date (customfield_10044), End date (customfield_10045), Description, Due date, Labels, Time tracking

---

## Technical Story (10528)

**必填**: Components, Client ID (customfield_10043), Technical Story Type (customfield_12348), issuetype, Priority, project, Summary  
**可选**: Assignee, Epic Link, Sprint, Story Points, Description, Due date, Fix versions, Labels, Parent

---

## Dev Bug (Sub-task) (11224) / UX Defect (Sub-task) (11291)

**必填**: issuetype, **Parent**, Priority, project, Summary  
**可选**: Assignee, Components, Epic Link, Sprint, Dev Bug Cause Category (customfield_12731), Description, Due date, Fix versions, Labels, Time tracking, Affects versions

---

## 常用自定义字段 key 对照

| 显示名 | key |
|--------|-----|
| Client ID | customfield_10043 |
| Epic Link / Parent | customfield_10014 |
| Sprint | customfield_10020 |
| Story Points | customfield_10033 |
| Story Type | customfield_10085 |
| Delivery Quarter | customfield_12899 |
| UX Review Required? | customfield_13319 |
| UX Review Status | customfield_13320 |
| Technical Story Type | customfield_12348 |
| Severity | customfield_10054 |
| Bug Source | customfield_12730 |

更新：`python3 scripts/jira/get_createmeta.py CP`
