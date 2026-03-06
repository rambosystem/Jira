# AGENTS.md

## Cursor Cloud specific instructions

### Repository overview

This is a **configuration-only repository** — it contains YAML governance files and a Cursor AI skill (`.cursor/skills/create-team-ticket/`) for automated Jira ticket creation across two Pacvue engineering teams:

- **CP (Campaign Platform)** — 11 product modules, config prefix `cp-*`
- **PAG (Pacvue Agent)** — 1 module, config prefix `pag-*`

There is **no application code, build system, or test suite**. The "application" is the `create-team-ticket` Cursor skill, which interacts with Jira via **Atlassian MCP tools** (e.g. `jira_search_fields`, `jira_get_user_profile`, `confluence_search_user`).

### File structure

| File pattern | Purpose |
|---|---|
| `*-team-board.config.yaml` | Team workspace config (project key, modules, members, defaults) |
| `*-ticket-issue-structures.yaml` | Required/optional fields per issue type |
| `*-epic-management.yaml` | Quarterly epic mappings and conventions |
| `*-sprint-management.yaml` | Sprint naming format and active sprint list |
| `*-label-management.yaml` | Roadmap and cross-team label conventions |
| `.cursor/skills/create-team-ticket/SKILL.md` | Cursor skill definition for ticket creation |
| `.cursor/skills/create-team-ticket/templates.md` | Bug/Task/Story/Epic description templates |

### Key facts

- **No dependencies** to install — no `package.json`, `requirements.txt`, `Makefile`, or `Dockerfile`.
- **No services** to start; the skill operates entirely within Cursor IDE using MCP server connections to Jira Cloud.
- All files are YAML or Markdown. Edits should preserve valid YAML syntax.

### Lint / validation

- `yamllint -d relaxed *.yaml` — validates YAML syntax (only line-length warnings expected).
- `python3 -c "import yaml; yaml.safe_load(open('file.yaml'))"` — quick parse check.
- Cross-reference validation: each `*-team-board.config.yaml` references companion files (epic/sprint/label management, issue structures). Verify referenced files exist when adding/renaming.

### Running the skill

The `create-team-ticket` skill requires a configured **Atlassian MCP server** connected to the Pacvue Jira instance. Without MCP access, the skill cannot create or validate tickets. The skill is invoked within Cursor's agent system — there is no standalone CLI entry point.

### Key gotchas

- The CP skill currently hard-references `cp-*.yaml` files. PAG has its own config set (`pag-*.yaml`) but the skill file references CP files only. To use the skill with PAG, the skill would need to be parameterized or duplicated.
- `board_filter.assignee_account_ids` in team configs must stay in sync with `team.members` account IDs.
- Epic/Sprint/Label management files are designed for quarterly rotation — update `recent_*` lists each quarter.
