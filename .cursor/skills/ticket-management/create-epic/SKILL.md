---
name: create-epic
description: Create Jira Epic tickets for the CP team. Use when user asks to create an Epic, quarterly epic, or Qn module epic. Read rules from config/policy/<project>/ticket-schema.json and naming from ticket-naming.yaml.
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

## Workflow

1. Resolve project from user input or `me.default_project`.
2. Validate component ownership and assignee.
3. Validate Delivery Quarter and other values against `ticket-schema.json`.
4. Run duplicate check.
5. Show Ticket Name List and get confirmation.
6. Create Epic.
7. Post-check key fields.
8. Insert the new Epic at the top of `config/assets/global/epic-list.yaml`.

## Output

- Before create: Ticket Name List, Confirmation Needed
- After create: Issue, URL, Type, Component, Assignee, Project, Validation, Validation Details