# Sprint Report Skill — Reference

## JQL 示例

- 完成 Story（按 Key 升序）  
  `project = CP AND issuetype = Story AND sprint = "26Q1-Sprint4-Defenders" AND statusCategory = Done ORDER BY key ASC`

## 建议请求字段

- `summary`, `status`, `assignee`, `key`, `components`
- 若有自定义「模块」字段，可一并请求用于分组。

## 输出模板结构

1. 标题：`# Sprint<N> Defenders 迭代总结（<sprint_name>）`
2. 引言：已完成 Story 共 **N** 条，按功能模块汇总如下。
3. 各模块：`## <模块名>` → 表格 `| Key | 内容 |` → `**迭代要点**：<一句话>`
4. 汇总表：`| 模块 | 完成 Story 数 | 主要方向 |`
5. 页脚：数据来源说明（项目、Sprint、statusCategory）。

## 模块名与配置对齐

- 分组后的模块名尽量与项目 component 列表一致（来自 `Jira/config/assets/project/CP/components.yaml` 或 `team.yaml` 的 `workspace.ownership.components`，如 Creative Hub → Creative Management）。
- 无法归入已知模块的 issue 可归为「其他」或单独成节。

## 模板文件

- 格式参考：工作区根目录 `Sprint4-Defenders-迭代总结.md`。
