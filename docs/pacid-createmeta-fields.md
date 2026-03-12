# PACID 项目创建工单字段（Create Metadata）

由 `scripts/jira/get_createmeta.py PACID` 从 Jira API 拉取，用于创建 PACID 工单时参考。

## 项目与 Issue 类型

- **Project**: PACID（Jira Product Discovery）
- **Issue 类型**: Idea (id=10037)、Roll-Up (id=10629)、New Retailer (id=10726)

## 必填字段（Required）

根据 Create Metadata API，三种类型在创建界面**均无**在 API 中标记为 required 的额外字段。  
创建 Issue 时仍需提供：

- **project**（key: PACID）
- **summary**（标题）
- **issuetype**（Idea / Roll-Up / New Retailer）

以上由 Jira 标准创建接口要求，createmeta 只返回「创建界面上的可选/额外字段」。

## Idea 类型可选字段（常用）

| 显示名 | key | 类型 |
|--------|-----|------|
| Assignee | assignee | user |
| Team | customfield_10001 | team |
| Start date | customfield_10015 | date |
| Goals | customfield_10090 | array |
| Impact | customfield_10267 | number |
| Teams | customfield_10278 | array |
| Score | customfield_10279 | number |
| Project start | customfield_10283 | string |
| Project target | customfield_10284 | string |
| Effort | customfield_10287 | number |
| Idea short description | customfield_10288 | string |
| PRD Document Link | customfield_10290 | string |
| GTM Feature Tier | customfield_10292 | option |
| Sizing | customfield_10485 | option |
| PRD Design Status | customfield_10489 | option |
| UX Status | customfield_10490 | option |
| Product Feature | customfield_10507 | array |
| Client Segment | customfield_10508 | array |
| UX Design Due Date | customfield_10510 | string |
| PRD Due Date | customfield_10511 | string |
| PME Sign Off Due Date | customfield_10512 | string |
| Priority (Idea) | customfield_10533 | option |
| US PM | customfield_10534 | array |
| Dev Leader | customfield_10548 | array |
| Release Status | customfield_10726 | option |
| UX Designer | customfield_10758 | array |
| Retailer/Platform | customfield_10791 | array |

完整列表见脚本输出：`python3 scripts/jira/get_createmeta.py PACID`。

## 如何更新本文档

```bash
python3 scripts/jira/get_createmeta.py PACID
```

如需其他项目，将 `PACID` 换成对应 project key 即可。
