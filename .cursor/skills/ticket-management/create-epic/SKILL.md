---
name: create-epic
description: Create Jira Epic tickets for the CP team. Use when user asks to create an Epic, quarterly epic, or Qn module epic. Create through MCP after showing the draft and getting confirmation. Read rules from config/policy/<project>/ticket-schema.json and naming from ticket-naming.yaml.
---

# Create Epic

## Purpose

Create Jira Epic tickets using workspace config and the project ticket schema.

## Config

- `Jira/config/assets/global/profile.yaml`: `me.default_project`
- `Jira/config/assets/project/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`
- `Jira/config/policy/<project>/ticket-schema.json`: `supported_work_types`, `defaults`, `issue_types.Epic`
- `Jira/config/policy/<project>/ticket-naming.yaml`: `naming.Epic`
- `Jira/config/assets/global/epic-list.yaml`: duplicate check and post-create update
- `Jira/config/assets/global/label-list.yaml`: roadmap and recent labels

## Preferred Execution

- Prefer MCP for Jira search, draft review, create, and link actions.

## Required Inputs

1. Summary
2. Component
3. Assignee
4. Delivery Quarter
5. Optional description

Default assignee should come from `ticket-schema.json` `defaults.assignee_by_work_type.Epic` when defined.

## Rules

- Validate Epic is listed in `ticket-schema.json` `supported_work_types`.
- Follow `ticket-schema.json` `issue_types.Epic.required_fields`, `optional_fields`, `field_options`, and `field_defaults`.
- Do not invent fields outside schema and Jira field mapping.
- Use naming from `ticket-naming.yaml`.
- Build the draft quickly from required fields plus applicable defaults.
- Do not include optional fields unless the user provided them or they are needed to review/create the issue.

## Workflow

1. Resolve project from user input or `me.default_project`.
2. Validate component ownership and assignee.
3. Validate Delivery Quarter and other values against `ticket-schema.json`.
4. Run duplicate check and prepare the draft.
5. Show a concise draft before any create action. Do not ask extra questions unless required information is missing or the user asks to adjust it.
6. Wait for user confirmation or correction.
7. Create Epic through MCP.
8. Post-check key fields.
9. Insert the new Epic at the top of `config/assets/global/epic-list.yaml` when local Epic cache should be refreshed.

## Output

- Before create: Concise Draft, Confirmation Needed
- After create: Issue, URL, Type, Component, Assignee, Project, Validation, Validation Details
