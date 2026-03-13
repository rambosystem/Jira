---
name: create-story
description: Create Jira Story tickets for the CP team. Assemble a structured issue plan first, then create through MCP after confirmation. Read rules from config/policy/<project>/ticket-schema.json and naming from ticket-naming.yaml.
---

# Create Story

## Purpose

Create Jira Story tickets using workspace config and the project ticket schema.

## Config

- `Jira/config/assets/global/profile.yaml`: `me.default_project`
- `Jira/config/assets/project/<project>/team.yaml`: `workspace.project.key`, `workspace.ownership.components`, `team.members`, `team.external_members`
- `Jira/config/policy/<project>/ticket-schema.json`: `supported_work_types`, `defaults`, `issue_types.Story`
- `Jira/config/policy/<project>/ticket-naming.yaml`: `naming.Story`
- `Jira/config/assets/global/epic-list.yaml`: parent resolution
- `Jira/config/assets/project/<project>/sprint-list.yaml`: sprint naming
- `Jira/config/assets/global/label-list.yaml`: roadmap and labels

## Preferred Execution

- Prefer MCP for Jira search, draft review, create, and link actions.

## Required Inputs

1. Summary
2. Component
3. Assignee
4. Story-specific required fields from `ticket-schema.json` `issue_types.Story`
5. Optional description
6. Optional `--link-pin`

Default assignee should come from `ticket-schema.json` `defaults.assignee`.
Default field values should come from `ticket-schema.json` `issue_types.Story.field_defaults`.

## Rules

- Validate Story is listed in `ticket-schema.json` `supported_work_types`.
- Follow `ticket-schema.json` `issue_types.Story.required_fields`, `optional_fields`, `field_options`, and `field_defaults`.
- Do not invent fields outside schema and Jira field mapping.
- Use naming from `ticket-naming.yaml`.
- Build the draft quickly from required fields plus applicable defaults.
- Do not include optional fields unless the user provided them or they are needed to review/create the issue.

## Workflow

1. Collect inputs.
2. Normalize title and assemble the required schema with defaults.
3. Show a concise draft before any create action. Do not ask extra questions unless required information is missing or the user asks to adjust it.
4. Resolve Epic/Parent in this order:
   - First, show the closest Epic match.
   - Prefer the module quarterly Epic for the selected quarter when available, e.g. `SOV -> SOV Upgrade - 26Q2`.
   - If no suitable Epic exists, note that no quarterly Epic was found and only ask to create one if the user wants to proceed that way.
5. Review only the key fields, parent recommendation, and duplicate check.
6. Wait for user confirmation or correction.
7. Create once from the confirmed plan through MCP.
8. If PIN keys are provided, create `Relates` links.
9. Post-check key fields.

## Output

- Before create: Concise Draft, Parent Recommendation, Confirmation Needed
- After create: Issue, URL, Type, Component, Assignee, Project, Validation, Validation Details
