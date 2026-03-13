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

## MCP Tools

- `jira_create_issue`
- `jira_get_issue` only for post-check when needed

## Required schema + defaults

- Build from `idea-middle-platform.yaml` only.
- Use `required_by_team` + `field_defaults` + user input.
- Use `description_template` only to shape the required description.
- Only pass fields defined in the YAML.

## Required Payload 模块（直接替换）

使用时将占位符替换为实际值，作为 `jira_create_issue` 的 `fields` 传入。

```json
{
  "project": { "key": "PACID" },
  "summary": "<SUMMARY>",
  "issuetype": { "name": "Idea" },
  "description": { "type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "<DESCRIPTION>"}]}] },
  "assignee": { "accountId": "<ACCOUNT_ID>" },
  "customfield_10278": [{ "value": "Ads" }],
  "customfield_10508": { "value": "Pacvue" },
  "customfield_10726": { "value": "<RELEASE_STATUS>" },
  "customfield_12866": [{ "value": "<ROADMAP_QUARTER>" }]
}
```

- **占位符**: `<SUMMARY>`=用户标题，`<DESCRIPTION>`=按 description_template 填写的正文，`<ACCOUNT_ID>`=field_defaults 或用户指定，`<RELEASE_STATUS>`=默认 "Discovery"，`<ROADMAP_QUARTER>`=如 "26Q2"（多选时为数组多项）。

## Rules

- PACID Idea still uses the PACID-specific issue-structure yaml.
- Only pass fields defined in `idea-middle-platform.yaml`.
- Do not invent extra fields.
- Use the template structure from `description_template`.
- Build the draft quickly from required fields plus applicable defaults.
- Do not include optional fields unless the user provided them or they are needed to review/create the issue.
- Do not run duplicate checks or show duplicate references.

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
