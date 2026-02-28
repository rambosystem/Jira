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
- sprint management in `cp-sprint-management.yaml`
- label management in `cp-label-management.yaml`

## Read Configuration First

Read `cp-team-board.config.yaml` and use:

- `workspace.project.key`
- `workspace.ownership.modules`
- `team.members`
- `ticketing.supported_work_types`
- `ticketing.defaults.assignee`
- `ticketing.defaults.assignee_by_work_type`
- `ticketing.defaults.client_id`
- `ticketing.epic_management_file`
- `ticketing.sprint_management_file`
- `ticketing.label_management_file`

Read `cp-ticket-issue-structures.yaml` and use:

- `issue_structures.Story`
- `issue_structures.Technical Story`
- `issue_structures.Epic`

Read `cp-epic-management.yaml` and use:

- `epic_management.module_quarter_default_epics`
- `epic_management.recent_epics`
- `epic_management.conventions`

Read `cp-sprint-management.yaml` and use:

- `sprint_management.format`
- `sprint_management.rules`
- `sprint_management.recent_sprints`

Read `cp-label-management.yaml` and use:

- `label_management.roadmap`
- `label_management.cross_team`
- `label_management.recent_labels`

## Required Inputs

Collect these fields before creating a ticket:

1. Issue type (must be in `ticketing.supported_work_types`)
2. Summary
3. Component (must be in `workspace.ownership.modules`)
4. Assignee (required; if missing, auto-fill by default rules)
5. Issue-type-specific required fields from `cp-ticket-issue-structures.yaml`

Description:

- Optional for all work types.
- Do not require description before creation.
- If user does not provide description, create ticket without description.

Optional:

- Priority
- Due date
- Links

For `Epic`, prefer title style:

- `<Module> Upgrade - <YYQn>`
- Example: `SOV Upgrade - 26Q2`
- If user asks with shorthand like "Q2 SOV epic", infer:
  - `Component = SOV`
  - `Delivery Quarter = Q2`
  - `Labels` includes `roadmap_26q2`
  - `Summary` and `Epic Name` use `SOV Upgrade - 26Q2`

For `Story` and `Technical Story`, enforce title style:

- `[模块] - [平台或范围] - [动作 + 对象]`
- Module should be bracketed, e.g. `[My Report]`, `[SOV]`
- For all-platform scope use `All Platforms`
- For multi-platform scope use slash format, e.g. `Amazon/Walmart/Target`
- Example titles:
  - `[My Report] - All Platforms - SOV Report 支持 Google Sheet`
  - `[SOV] - Amazon - Add New Metrics SB Banner`

## Creation Workflow

0. Infer defaults from concise user intent (when possible):
   - If user mentions `epic`, set Issue type = `Epic`.
   - If user input contains `<Qn> <Module>` pattern (e.g. `Q2 SOV`), derive:
     - `Component` from module token.
     - `Delivery Quarter` from quarter token.
     - roadmap label from quarter token (e.g. `Q2` -> `roadmap_26q2` for year `26`).
     - `Summary/Epic Name` using `<Module> Upgrade - <YYQn>`.
   - If user does not provide assignee for `Epic`, use work-type default assignee.
1. Validate required fields:
   - `workspace.project.key` exists.
   - Issue type is in `ticketing.supported_work_types`.
   - Component is in `workspace.ownership.modules`.
   - Assignee exists in `team.members`.
   - All required fields for the selected issue type are present per `cp-ticket-issue-structures.yaml`.
   - If a provided field value has options in `field_options`, validate against the allowed options.
   - If `Client ID` is missing, default to `ticketing.defaults.client_id` (`0000`).
   - For `Story`, apply defaults from `issue_structures.Story.field_defaults` when user does not specify:
     - `Client ID = 0000`
     - `UX Review Required? = No`
     - `UX Review Status = Not Needed`
   - Validate sprint using `cp-sprint-management.yaml`:
     - Format should follow `YYQn-Sprintm-Defenders` (for example `26Q1-Sprint6-Defenders`).
     - Default rule: each quarter has 6 sprints (`Sprint1` to `Sprint6`).
     - Prefer values from `sprint_management.recent_sprints.values` when selecting/confirming Sprint.
   - Validate labels using `cp-label-management.yaml`:
     - Standard roadmap label should follow `roadmap_YYqN` (for example `roadmap_26q1`, `roadmap_26q2`).
     - If the work involves cross-team collaboration, include `cross-team` label.
     - Prefer values from `label_management.recent_labels` when selecting/confirming Labels.
   - Resolve `Parent` for Story/Technical Story using `cp-epic-management.yaml`:
     - Always prioritize `cp-epic-management.yaml` as the source of Parent candidates.
     - For functional-module work, default to the module quarterly Epic when mapping exists.
     - If user specifies a special Epic, use the user-specified Epic.
     - If no suitable Parent can be matched from `cp-epic-management.yaml`, ask user for Parent confirmation before creation.
2. Run duplicate check before create:
   - Search Jira for same project + issue type + summary.
   - For Epic quarterly naming, check existing `<Module> Upgrade - <YYQn>` first.
   - If duplicate exists, ask user whether to reuse existing issue or create a new one.
3. Normalize assignee to `account_id`.
   - Assignee is treated as required for all ticket types.
   - If assignee is missing and work type is `Epic`, use `ticketing.defaults.assignee_by_work_type.Epic` (Rambo Wang).
   - Otherwise use `ticketing.defaults.assignee` (Xuanyu Liu, Dev Leader).
4. Build summary:
   - For `Story` and `Technical Story`, use the naming style in this skill.
   - For `Epic`, prefer `<Module> Upgrade - <YYQn>`.
5. Build issue description only when user provides description content.
   - Description is optional and should not block ticket creation.
   - If provided, use template guidance from `templates.md`.
   - Ensure acceptance criteria checklist uses strict markdown syntax: `- [ ]`.
6. Before calling any Jira MCP tool, read that tool schema/descriptor first.
7. Resolve custom field ids before create/update:
   - Use `jira_search_fields` for:
     - `Delivery Quarter`
     - `Epic Name`
     - `Client ID` (if needed by issue type/screen)
   - Pass these through `additional_fields` using discovered `customfield_xxxxx`.
8. Create Jira issue with:
   - Project = `workspace.project.key`
   - Issue type = selected type
   - Summary = user summary
   - Assignee = resolved `account_id`
   - Component = selected component
   - Description = optional (only include when provided)
9. Return:
   - issue key
   - issue URL
   - fields used for creation

## Guardrails

- Do not use components outside `workspace.ownership.modules`.
- If assignee is ambiguous, ask for confirmation.
- If required fields are missing, ask concise follow-up questions.
- Do not invent issue-type fields; follow `cp-ticket-issue-structures.yaml`.
- Treat `Labels` and `Assignee` as required for all ticket types.
- Treat `Parent` and `Sprint` as required for `Story`/`Technical Story`, but optional for `Epic`.
- Treat `Summary` as the ticket name.
- Default ticket `Priority` to `Medium` when not specified.
- Default `Client ID` to `0000` when not specified.
- If assignee is not provided, auto-fill work-type default first, then fallback to global default assignee.
- Enforce sprint convention: `YYQn-Sprintm-Defenders`, with `m` in `1..6`.
- Enforce label convention: roadmap labels use `roadmap_YYqN`; cross-team work must include `cross-team`.
- For Story/Technical Story Parent, use `cp-epic-management.yaml` first; if unmatched, ask user before creating.
- When creating tickets, prioritize selecting Sprint/Labels from the corresponding recent lists.
- For `Story`, default `UX Review Required?` to `No`; only set `Yes` when user explicitly requests UX review.
- For `Story` and `Technical Story`, enforce the naming format defined in this skill.
- For `Epic`, use `<Module> Upgrade - <YYQn>` unless user explicitly requests different naming.
- Always perform duplicate check by summary before creating a new issue.
- Always discover custom-field ids via `jira_search_fields` before setting `additional_fields`.
- Never block creation due to missing description.
- Keep summary and description clear and actionable.

## Output Format

After issue creation, respond with:

- `Issue`: `<KEY>`
- `URL`: `<LINK>`
- `Type`: `<work_type>`
- `Component`: `<component>`
- `Assignee`: `<name> (<account_id>)`
- `Project`: `<workspace.project.key>`
