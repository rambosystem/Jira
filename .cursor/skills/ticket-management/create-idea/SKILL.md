---
name: create-idea
description: Create PACID Idea tickets for the Middle Platform team. Use config/policy/PACID/issue-structures/idea-middle-platform.yaml as the only source of required fields, defaults, and description template.
---

# Create Idea (PACID)

## Purpose

Create PACID Idea tickets for the Middle Platform team.

## Config

- `config/policy/PACID/issue-structures/idea-middle-platform.yaml`: `required_by_team`, `description_template`, `field_defaults`
- `config/assets/global/profile.yaml`: default assignee information

## Rules

- PACID Idea still uses the PACID-specific issue-structure yaml.
- Only pass fields defined in `idea-middle-platform.yaml`.
- Do not invent extra fields.
- Use the template structure from `description_template`.

## Required Inputs

1. Summary
2. Description
3. Assignee
4. Release Status
5. Roadmap Quarter

## Workflow

1. Read `config/policy/PACID/issue-structures/idea-middle-platform.yaml`.
2. Collect required inputs.
3. Build additional Jira custom fields only from this yaml.
4. Create the PACID Idea.
5. Optionally ask whether to create and link a CP Epic.
6. If Epic is created, update `config/assets/global/epic-list.yaml`.

## Output

- Before create: summary of required fields and confirmation
- After create: Issue key, URL, Summary, Assignee, Release Status, Roadmap Quarter