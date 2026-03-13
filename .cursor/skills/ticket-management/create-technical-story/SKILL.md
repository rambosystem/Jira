---
name: create-technical-story
description: Create Jira Technical Story tickets for the CP team. Assemble a structured issue plan first, then create through MCP after confirmation. Read rules from config/policy/<project>/ticket-schema.json and naming from ticket-naming.yaml.
---

# Create Technical Story

## Purpose

Create Jira Technical Story tickets using workspace config and the project ticket schema.

## Config

- `Jira/config/assets/global/profile.yaml`: `me.default_project`
- `Jira/config/assets/project/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`
- `Jira/config/policy/<project>/ticket-schema.json`: `supported_work_types`, `defaults`, `issue_types.Technical Story`
- `Jira/config/policy/<project>/ticket-naming.yaml`: `naming.Technical Story`
- `Jira/config/assets/global/epic-list.yaml`: parent resolution
- `Jira/config/assets/project/<project>/sprint-list.yaml`: sprint naming
- `Jira/config/assets/global/label-list.yaml`: roadmap and labels

## Preferred Execution

- Prefer MCP for Jira search, draft review, create, and link actions.

## Required Inputs

1. Summary
2. Component
3. Assignee
4. Technical Story required fields from `ticket-schema.json` `issue_types.Technical Story`
5. Optional description
6. Optional `--link-pin`

Default assignee should come from `ticket-schema.json` `defaults.assignee`.
Default field values should come from `ticket-schema.json` `issue_types.Technical Story.field_defaults`.

## Rules

- Validate Technical Story is listed in `ticket-schema.json` `supported_work_types`.
- Follow `ticket-schema.json` `issue_types.Technical Story.required_fields`, `optional_fields`, `field_options`, and `field_defaults`.
- Do not invent fields outside schema and Jira field mapping.
- Use naming from `ticket-naming.yaml`.
- Build the draft quickly from required fields plus applicable defaults.
- Do not include optional fields unless the user provided them or they are needed to review/create the issue.

## Workflow

1. Collect inputs.
2. Normalize title and assemble the required schema with defaults.
3. Show a concise draft before any create action. Do not ask extra questions unless required information is missing or the user asks to adjust it.
4. Do not require Epic/Parent. Default Parent to empty unless the user explicitly provides one.
5. Review only the key fields, duplicate check, and optional parent.
6. Wait for user confirmation or correction.
7. Create once from the confirmed plan through MCP.
8. If PIN keys are provided, create `Relates` links.
9. Post-check key fields.

## Output

- Before create: Concise Draft, Optional Parent, Confirmation Needed
- After create: Issue, URL, Type, Component, Assignee, Project, Validation, Validation Details
