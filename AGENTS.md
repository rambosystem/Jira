# AGENTS.md

## Cursor Cloud specific instructions

### Repository overview

This is a **configuration-only repository** — there is no application code, build system, tests, or runnable services. It contains:

- **YAML config files** for two Pacvue teams (CP / PAG) governing Jira ticket creation, sprint/epic/label management, and board filters.
- **Cursor AI skill** (`.cursor/skills/create-team-ticket/`) that reads these configs at runtime and drives Jira ticket workflows via MCP (Atlassian) tools.

### Key facts

- **No dependencies** to install — no `package.json`, `requirements.txt`, `Makefile`, or `Dockerfile`.
- **No lint / test / build** steps exist.
- **No services** to start; the skill operates entirely within Cursor IDE using MCP server connections to Jira Cloud.
- All files are YAML or Markdown. Edits should preserve valid YAML syntax.

### Working with this repo

- To validate config files are well-formed, use Python's `yaml.safe_load()` (PyYAML is pre-installed).
- Cross-reference integrity matters: team board configs reference epic/sprint/label management files by filename. Keep these references consistent when renaming files.
- The `create-team-ticket` skill in `.cursor/skills/` has a companion `templates.md` for issue description templates.
- The skill requires an active Atlassian/Jira MCP server connection to function (ticket creation, user lookup, field discovery). Without MCP, the skill definition can only be read, not executed.
