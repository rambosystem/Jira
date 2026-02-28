---
name: create-team-ticket
description: Create Jira tickets for the CP team using workspace configuration, including project key, supported work types, owned modules, and team members. Use when user asks to create tickets, assign owners, choose components, or generate ticket drafts.
---

# Create Team Ticket

## Purpose

Create Jira tickets in a consistent format using:
- team configuration in `cp-team-board.config.yaml`
- issue field structure in `cp-ticket-issue-structures.yaml`
- quarterly epic management in `cp-epic-management.yaml`

## Read Configuration First

Read `cp-team-board.config.yaml` and use:
- `workspace.project.key`
- `workspace.ownership.modules`
- `team.members`
- `ticketing.supported_work_types`
- `ticketing.defaults.assignee`
- `ticketing.epic_management_file`

Read `cp-ticket-issue-structures.yaml` and use:
- `issue_structures.Story`
- `issue_structures.Technical Story`

Read `cp-epic-management.yaml` and use:
- `epic_management.module_quarter_default_epics`
- `epic_management.recent_epics`
- `epic_management.conventions`

## Required Inputs

Collect these fields before creating a ticket:
1. Issue type (must be in `ticketing.supported_work_types`)
2. Summary
3. Component (must be in `workspace.ownership.modules`)
4. Assignee (optional; default to `ticketing.defaults.assignee`)
5. Description details (background, goal, acceptance criteria)
6. Issue-type-specific required fields from `cp-ticket-issue-structures.yaml`

Optional:
- Priority
- Due date
- Labels
- Links

For `Story` and `Technical Story`, enforce title style:
- `[模块] - [平台或范围] - [动作 + 对象]`
- Module should be bracketed, e.g. `[My Report]`, `[SOV]`
- For all-platform scope use `All Platforms`
- For multi-platform scope use slash format, e.g. `Amazon/Walmart/Target`
- Example titles:
  - `[My Report] - All Platforms - SOV Report 支持 Google Sheet`
  - `[SOV] - Amazon - Add New Metrics SB Banner`

## Creation Workflow

1. Validate required fields:
   - `workspace.project.key` exists.
   - Issue type is in `ticketing.supported_work_types`.
   - Component is in `workspace.ownership.modules`.
   - Assignee exists in `team.members`.
   - All required fields for the selected issue type are present per `cp-ticket-issue-structures.yaml`.
   - If a provided field value has options in `field_options`, validate against the allowed options.
   - For `Story`, apply defaults from `issue_structures.Story.field_defaults` when user does not specify:
     - `UX Review Required? = No`
     - `UX Review Status = Not Needed`
   - Validate sprint using `issue_structures.<type>.field_options.Sprint`:
     - Format should follow `YYQn-Sprintm-Defenders` (for example `26Q1-Sprint6-Defenders`).
     - Default rule: each quarter has 6 sprints (`Sprint1` to `Sprint6`).
   - Validate labels using `issue_structures.<type>.field_options.Labels`:
     - Standard roadmap label should follow `roadmap_YYqN` (for example `roadmap_26q1`, `roadmap_26q2`).
     - If the work involves cross-team collaboration, include `cross-team` label.
   - Resolve `Parent` for Story/Technical Story using `cp-epic-management.yaml`:
     - For functional-module work, default to the module quarterly Epic when mapping exists.
     - If user specifies a special Epic, use the user-specified Epic.
     - If no mapping exists for the module/quarter and user did not specify special Epic, ask for Parent confirmation.
2. Normalize assignee to `account_id`.
   - If assignee is missing, use `ticketing.defaults.assignee` (Xuanyu Liu, Dev Leader).
3. Build summary:
   - For `Story` and `Technical Story`, use the naming style in this skill.
4. Build issue description using the template in `templates.md`.
5. Before calling any Jira MCP tool, read that tool schema/descriptor first.
6. Create Jira issue with:
   - Project = `workspace.project.key`
   - Issue type = selected type
   - Summary = user summary
   - Assignee = resolved `account_id`
   - Component = selected component
   - Description = normalized template output
7. Return:
   - issue key
   - issue URL
   - fields used for creation

## Guardrails

- Do not use components outside `workspace.ownership.modules`.
- If assignee is ambiguous, ask for confirmation.
- If required fields are missing, ask concise follow-up questions.
- Do not invent issue-type fields; follow `cp-ticket-issue-structures.yaml`.
- If assignee is not provided, assign to `ticketing.defaults.assignee`.
- Enforce sprint convention: `YYQn-Sprintm-Defenders`, with `m` in `1..6`.
- Enforce label convention: roadmap labels use `roadmap_YYqN`; cross-team work must include `cross-team`.
- For Story/Technical Story Parent, default to module quarterly Epic; allow explicit special-Epic override.
- For `Story`, default `UX Review Required?` to `No`; only set `Yes` when user explicitly requests UX review.
- For `Story` and `Technical Story`, enforce the naming format defined in this skill.
- Keep summary and description clear and actionable.

## Output Format

After issue creation, respond with:

- `Issue`: `<KEY>`
- `URL`: `<LINK>`
- `Type`: `<work_type>`
- `Component`: `<component>`
- `Assignee`: `<name> (<account_id>)`
- `Project`: `<workspace.project.key>`
