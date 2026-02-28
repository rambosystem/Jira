# Progress Log

## 2026-02-28

- Created `cp-team-board.config.yaml` from provided team board JQL.
- Resolved all listed Jira `accountId` values to user names via Atlassian MCP.
- Added a `users` mapping section into `cp-team-board.config.yaml` for quick lookup and maintenance.
- Restructured `cp-team-board.config.yaml` into workspace-oriented sections: `workspace` (project/modules/members) and `board_filter`.
- Enriched member entries with `name`, `account_id`, and `email` for easier team management.
- Created project skill `.cursor/skills/create-team-ticket/SKILL.md` for standardized CP ticket creation workflow.
- Added `.cursor/skills/create-team-ticket/templates.md` with Bug, Task, and Story description templates.
- Added `workspace.supported_work_types` for CP and set it to: Story, Technical Story, Bug, Epic, Sub-task, Dev Bug (Sub-task).
- Synced `board_filter.issue_types`, JQL issue type clause, and skill validation text to use the selected six work types.
- Added `workspace.ticket_naming` convention and supported platform list for Feature/Technical Story title formatting.
- Updated `create-team-ticket` skill to enforce Story/Technical Story summary format: `[模块] - [平台或范围] - [动作 + 对象]`.
- Added two official naming examples to config and skill:
  - `[My Report] - All Platforms - SOV Report 支持 Google Sheet`
  - `[SOV] - Amazon - Add New Metrics SB Banner`
- Corrected JQL issue type clause back to the selected six work types.
- Added standalone YAML `cp-ticket-issue-structures.yaml` to persist Story and Technical Story field structure, required/optional fields, and key option lists.
- Updated `create-team-ticket` skill to consume `cp-ticket-issue-structures.yaml` for required fields and option validation (instead of hardcoded issue field details).
- Updated `cp-ticket-issue-structures.yaml`: marked `Sprint`, `Labels`, and `Parent` as required for both Story and Technical Story.
- Added ticket default assignee in `cp-team-board.config.yaml`: Xuanyu Liu (`account_id: 712020:56137117-3aff-4ea4-b5b5-59aae5ad5235`, role `Dev Leader`).
- Added Labels convention to issue structures: roadmap labels use `roadmap_YYqN` and cross-team work must include `cross-team`.
- Added Sprint convention to issue structures: `YYQn-Sprintm-Defenders`, with 6 sprints per quarter.
- Updated skill validation/guardrails to enforce default assignee, Sprint format/range, and Labels convention.
- Added Story defaults: `UX Review Required? = No` and `UX Review Status = Not Needed`; skill now applies these unless user explicitly asks for UX review.
- Added `ticketing.epic_management` into `cp-team-board.config.yaml` with 20 recent epics and quarterly module parent strategy.
- Added quarterly module default epic mapping for `26Q1` (`Dayparting Scheduler` -> `CP-44089`, `SOV` -> `CP-44087`, `My Report` -> `CP-44086`).
- Updated skill to resolve Story/Technical Story `Parent` via quarterly module epics, with explicit special-Epic override.
- Split quarterly epic management into standalone `cp-epic-management.yaml` for easier quarter-by-quarter maintenance.
- Simplified `cp-team-board.config.yaml` to reference `ticketing.epic_management_file` instead of embedding epic data.
- Updated skill to read parent-resolution conventions and epic mappings from `cp-epic-management.yaml`.
- Removed `status` from `cp-epic-management.yaml` recent epic entries; keep only key/title/date for lightweight maintenance.
- Queried Jira with JQL `project = CP AND issuetype = Epic AND reporter = "Rambo Wang" ORDER BY created DESC` and retrieved the latest 50 matching epics.
