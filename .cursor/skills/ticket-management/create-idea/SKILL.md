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
- Build the draft quickly from required fields plus applicable defaults.
- Do not include optional fields unless the user provided them or they are needed to review/create the issue.

## Required Inputs

1. Summary
2. Description
3. Assignee
4. Release Status
5. Roadmap Quarter

## Workflow

1. Read `config/policy/PACID/issue-structures/idea-middle-platform.yaml`.
2. Collect required inputs.
3. Build the required Jira fields only from this yaml.
4. Show a concise draft before any create action. Do not ask extra questions unless required information is missing or the user asks to adjust it.
5. Wait for user confirmation or correction.
6. Create the PACID Idea.
7. Only discuss creating/linking a CP Epic if the user explicitly asks for it.
8. If Epic is created, update `config/assets/global/epic-list.yaml`.

## Output

- Before create: Concise Draft, Confirmation Needed
- After create: Issue key, URL, Summary, Assignee, Release Status, Roadmap Quarter
