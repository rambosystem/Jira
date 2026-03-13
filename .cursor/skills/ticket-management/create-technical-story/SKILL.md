---
name: create-technical-story
description: Create Jira Technical Story tickets for the CP team. Prefer assembling a structured issue plan first, then creating once. Read rules from config/policy/<project>/ticket-schema.json and naming from ticket-naming.yaml.
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

- Prefer `scripts/jira/assemble_jira_issue.py` then `scripts/jira/create_jira_issue.py`
- Use `scripts/jira/query_issues.py --jql "<JQL>"` for Jira searches
- Use MCP only as fallback

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

## Workflow

1. Collect inputs.
2. Normalize title and show Ticket Name List.
3. Assemble a structured issue plan first.
4. Review resolved parent/defaults/fields.
5. Create once from the plan.
6. If PIN keys are provided, create `Relates` links.
7. Post-check key fields.

## Output

- Before create: Ticket Name List, Confirmation Needed
- After create: Issue, URL, Type, Component, Assignee, Project, Validation, Validation Details
