# Jira Workspace Guidance

- When users refer to "unaccepted tickets," they are referring to tickets within a Sprint that are in the "Acceptance Testing" status.

- When a task involves time or dates (e.g. current Sprint, "today", reporting period), obtain the current system time by running a command.

# MCP Tools

- mcp-atlassian, Jira and Confluence Management Services

## Execution Preference

- Prefer MCP for Jira and Confluence operations such as query, create, update, link, and other direct remote actions.
- Use local scripts only when they are clearly more efficient, provide needed batching/formatting/validation, or cover capabilities MCP cannot reliably provide.
- Do not introduce a script-first workflow for tasks that MCP can already handle cleanly.

## Engineering Level

- Add engineering structure only when it improves reliability, reuse, or clarity for this workspace.
- Keep implementations pragmatic and lightweight; avoid over-engineering, unnecessary abstractions, or multi-layer flows for simple tasks.
- Prefer the simplest path that still preserves reviewability, correctness, and maintainability.
