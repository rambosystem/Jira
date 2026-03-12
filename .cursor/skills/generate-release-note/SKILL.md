---
name: generate-release-note
description: Generate a Release Note from Sprint Report data in the standard format—product sections with version, "For Platform" groups, Update/New bullets, and a details link. Use when user asks for release note, release notes, 发版说明, or "based on Sprint N / 迭代总结 generate release note".
---

# Generate Release Note

## Purpose

Produce a **Release Note** document in the team's standard style, **based on completed Stories from a Sprint** (Sprint Report / 迭代总结). The output is structured by product/module, then by platform, with each item labeled as **Update** or **New**, and ends with a "more details" link.

## When to Use

- User asks to "generate release note" or "写发版说明" from a sprint
- User says "based on Sprint N" or "基于迭代总结生成 Release Note"
- User provides a version (e.g. V3.29) and/or a Confluence/details URL and wants the note filled from sprint completion data

## Release Note Format (Required Style)

Follow this structure for each product section:

```markdown
#### <Product Name> V<version>

For <Platform>：

- Update: <short description>
- New: <short description>

For <Other Platform>:

- Update: <short description>

Click [here](details_url) for more details.
```

**Rules:**

- **Heading**: `####` (h4) + Product name + space + `V<version>` (e.g. `#### Budget Manager V3.29`).
- **Platform blocks**: `For Amazon：`, `For Reddit:`, `For Walmart:`, etc. Use colon `：` or `:` after the platform. One block per platform; use "For All Platforms:" when the work is not platform-specific.
- **Bullets**: Start with `Update:` or `New:` then a short, user-facing phrase in English (or the language the user requests).
- **Details link**: One per product section: `Click [here](<url>) for more details.`

## Data Source: Sprint Report

- **Input**: The same data used for Sprint Report—completed (Done) Stories in a given Defenders sprint.
- **How to get it**:
  1. Resolve project: from user input or `me.default_project` in `Jira/assets/global/profile.yaml`.
  2. Resolve sprint name (e.g. "Sprint4" → `26Q1-Sprint4-Defenders`) using `Jira/assets/<project>/sprint-list.yaml` and `Jira/assets/<project>/team.yaml` as in the **sprint-report** skill.
  3. Query Jira using the `sprint_done_stories` template from `Jira/assets/<project>/query-templates.yaml` with `project` and `sprint_name` substituted, or use JQL: `project = <project> AND issuetype = Story AND sprint = "<sprint_name>" AND statusCategory = Done`, fields `summary`, `key`, `components`.
  4. Group issues by **module** (component or inferred from summary), same as Sprint Report.

Do **not** invent stories; only include issues returned by this query (or from an existing Sprint Report file if the user points to it).

## Workflow

1. **Get sprint completion data**
   - If user says "based on Sprint N" or "从 Sprint N 生成": resolve sprint name, run Jira search as above, group by module.
   - If user points to an existing file (e.g. `Sprint4-Defenders-迭代总结.md`): parse that file to get per-module lists of Story keys and 内容/summaries; optionally re-query Jira by key for `components` if needed for product name.

2. **Resolve version and details URL**
   - **Version**: Use if user provides (e.g. "V3.29"). If not provided, use a placeholder like `Vx.xx` or ask.
   - **Details URL**: Use if user provides (e.g. Confluence link). If not, use placeholder `https://pacvue-enterprise.atlassian.net/wiki/...` or ask.

3. **Map module → product name**
   - Use a consistent mapping for Release Note titles. Examples (customize per project):
     - Budget Scheduler → **Budget Manager**
     - Dayparting Scheduler → **Dayparting** or **Dayparting Scheduler**
     - My Report → **My Report**
     - SOV → **SOV**
     - Calendar Center → **Calendar Center**
     - Creative Management / Creative Hub → **Creative Hub**
   - If no mapping is defined, use the module name as the product name.

4. **For each module (product)**  
   For each group of stories:
   - **Extract platform** from each story summary (e.g. "Amazon", "Reddit", "Walmart", "Target", "Kroger", "Doordash", "Criteo", "TikTok", "All Platforms", "MX" → Walmart MX). Put platform-agnostic or "All Platforms" stories in a "For All Platforms:" block.
   - **Classify each item** as **New** or **Update**:
     - **New**: Rollout, first-time support, "Rollout ... to X", "支持 X" (first time), "New Version Support" for a new platform, or summary clearly indicating net-new capability.
     - **Update**: Everything else (improvements, fixes, new fields, optimizations).
   - **Write one bullet per story** (or merge very similar ones): `Update: <description>` or `New: <description>`. Description = short, user-facing English phrase derived from the story summary (e.g. "Allow users to save the filter", "Rollout Budget Manager to Reddit").

5. **Build the document**
   - One `#### Product V<version>` section per product.
   - Under each product: "For <Platform>:" blocks, then bullets, then `Click [here](<url>) for more details.`
   - Order sections by product (e.g. follow the project's component list order from team/components or alphabetically).

6. **Output**
   - Write to a file, e.g. `Release-Note-Sprint<N>-Vx.xx.md` or `Release-Note-<sprint_name>.md`.
   - Reply with the file path and a one-line summary (e.g. "Generated release note for Sprint4, 7 products, see Release-Note-Sprint4.md").

## New vs Update (Guidelines)

| Signal in summary / title                                | Prefer                   |
| -------------------------------------------------------- | ------------------------ |
| Rollout, 接入, 支持 &lt;Platform&gt; (first time)        | New                      |
| New Version Support (for a new platform)                 | New                      |
| 新增, Add new &lt;X&gt; (new feature)                    | New (or Update if minor) |
| Update, 优化, 修复, Allow users to..., Add &lt;field&gt> | Update                   |
| 交互优化, 补偿机制, 埋点                                 | Update                   |

When in doubt, use **Update**.

## Guardrails

- Only include stories that are in the sprint and Done; do not add or guess items.
- Keep bullet text short and user-facing (no Jira keys or internal jargon in the bullet text; keys can appear in a footnote or details page if needed).
- Preserve the exact style: `####`, `For <Platform>:`, `Update:` / `New:`, and `Click [here](...)`.
- If the user provides a Confluence or wiki URL, use it for "more details"; otherwise leave a placeholder or ask.

## Reference

- **Style example** (user-provided):

```markdown
#### Budget Manager V3.29

For Amazon：

- Update: Allow users to save the filter
- Update: Add a notification when the client saves 0 budget in BM

For Reddit:

- New: Rollout Budget Manager to Reddit

Click [here](https://pacvue-enterprise.atlassian.net/wiki/x/zIJMSg) for more details.
```

- **Data source**: Same as **sprint-report** skill (Jira query by sprint + statusCategory = Done, group by module; project from `Jira/assets/global/profile.yaml` `me.default_project` or user; config from `Jira/assets/<project>/sprint-list.yaml`, `team.yaml`, `query-templates.yaml`). Optionally reuse or parse `Sprint<N>-Defenders-迭代总结.md` if it already exists.
