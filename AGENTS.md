# Jira Workspace Guidance

## Execution Preference

- Prefer MCP for Jira and Confluence operations such as query, create, update, link, and other direct remote actions.
- Use local scripts only when they are clearly more efficient, provide needed batching/formatting/validation, or cover capabilities MCP cannot reliably provide.
- Do not introduce a script-first workflow for tasks that MCP can already handle cleanly.

## Engineering Level

- Add engineering structure only when it improves reliability, reuse, or clarity for this workspace.
- Keep implementations pragmatic and lightweight; avoid over-engineering, unnecessary abstractions, or multi-layer flows for simple tasks.
- Prefer the simplest path that still preserves reviewability, correctness, and maintainability.

## Creation Flow

- For create flows, assemble the required schema and defaults directly and efficiently; do not turn simple creation into a long exploratory process.
- Always show a draft before creating, but keep the draft concise and focused on the key fields needed for review.
- Do not ask follow-up questions after showing the draft unless the flow is blocked by missing required information or the user explicitly asked for options.
- Do not include non-required fields in the draft or create payload unless the user explicitly provided them, explicitly asked for them, or the target system requires them.
- If defaults are applied to required fields, use them silently in the draft unless they are material to review.
