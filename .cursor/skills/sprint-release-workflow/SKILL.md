---
name: sprint-release-workflow
description: Generate Sprint-based Release Note Summary for CP and create blank Confluence detail pages under the correct APRN module directories first, then output markdown with Click-here links. Use when user asks for Sprint updates + Release Note Summary + empty page creation workflow.
---

# `sprint-release-workflow` Sprint Release Workflow

## Safety Rule (HARD — never violate)

The Confluence **Release Notes Summary page is shared/public**. This skill MUST
NOT modify it under any circumstance.

- NEVER call `confluence_update_page`, `confluence_create_page`,
  `confluence_delete_page`, `confluence_add_comment`, or any other write tool
  against `release_note_summary_page_id` or any page ancestor/descendant in
  the Summary page chain.
- READ-only access (`confluence_get_page`, `confluence_search`) on the
  Summary page is allowed, and only for version inspection.
- All Summary updates are performed by the **user**, by manually pasting the
  generated tmp file (Step 4.5) in the Confluence editor.
- If the user explicitly asks the skill to "publish to Summary" / "update
  Summary page" / similar, refuse and re-state this rule, then offer the
  tmp-file path instead.

## Purpose

Standardize this workflow for CP release operations:

1. Collect Sprint updates (Story-focused).
2. Create blank Confluence detail pages under the correct module directories.
3. Generate Release Note Summary markdown and fill `Click [here](...)` links.

## When To Use

Use this skill when the user asks to:

- summarize Sprint updates for release notes
- generate Release Note Summary in fixed markdown format
- create blank Confluence detail pages first, then write summary

## Required Config

Read:

- `config/assets/project/CP/component-versions.yaml`

This file must contain:

- `component_versions` (component -> version string)
- `release_note_summary_page_id` (default Summary page id, preferred for API operations)
- `release_note_parent_pages` (component -> Confluence parent page id in APRN)

Current critical components:

- `Budget Scheduler`
- `Dayparting Scheduler`
- `My Report`

## Required Output Format

For each component:

```markdown
#### <Component> V<version>

For <Platform>

- Update: <text>

Click [here](detail_page_url) for details.
```

If user asks for markdown source, output fenced markdown only.

## Execution Order (Strict)

### Step -1: Confirm Release Window and Section Anchor

Before any other step, confirm the release window and the Summary section anchor.

1. Ask the user for the release window (for example `4.28`).
2. Convert it to formal anchor `<Mon>/<DD>/<YYYY> Middle Platform`
   (for example `Apr/28/2026 Middle Platform`).
3. Open the Summary page using `release_note_summary_page_id` and search for an
   existing `## <date> Middle Platform` section. This is for **read-only**
   inspection (see Step 4.5 — we never write back to the Summary page).
4. Decide output mode for Step 4.5:
   - If the section does not exist on the Summary page: write a fresh dated
     section into the tmp file.
   - If the section exists: still write a fresh dated section into the tmp
     file containing only the in-scope modules; the user will paste it into
     the existing section manually.
5. Never duplicate an existing module section in the same window. If a target
   module already has a section in the Summary page for the window, ask user
   whether to replace, merge, or skip — and reflect the decision in the tmp
   file (skip the module, or include with a `<!-- replace -->` marker).

### Step 0: Read Summary and Validate Versions

Before workflow execution, read the Summary page using `release_note_summary_page_id`.

1. Parse latest module versions from Summary sections (for example `#### My Report V1.17`).
2. Compare parsed versions with local `component_versions`.
3. If mismatches exist, show the diff and use Summary as source of truth for this run.
4. Keep an in-memory version map for this run (do not write file yet).

### Step 1: List Sprint Candidates

1. Resolve Sprint target from user input (for CP, use configured sprint ids/names).
2. Query Jira issues for that Sprint. The `fields` arg MUST include
   `customfield_10085` (Story Type) in addition to
   `summary,issuetype,components`. Without it, Step 4's bullet prefix
   classification cannot run.
3. Default to `issuetype = Story` unless user asks for all types.
4. Apply user filters (for example: exclude Creative Hub/Management).
5. Present the resulting candidate list back to the user as a numbered table:
   `# | Key | Component | Story Type | Summary`. Do NOT proceed past this step
   without explicit user confirmation in Step 1.5.

### Step 1.5: User Confirms Release Scope (HARD gate)

Not every Story in a Sprint needs a release note. The user must hand-pick the
in-scope subset before any downstream step runs.

1. Ask the user to confirm the in-scope set in one of these forms:
   - explicit keys (for example `CP-123, CP-456`)
   - row numbers from the Step 1 table (for example `1, 3, 5-7`)
   - `all` to include every candidate
   - `none` to abort the workflow
2. Default behavior is **NOT** "all". If the user replies ambiguously, ask again.
3. Lock the confirmed set as the working scope. All later steps (component
   grouping, page creation, summary generation, version update) operate only
   on this confirmed scope.
4. If the user later asks to add/remove a Story mid-run, restart from Step 2
   with the updated scope (do not silently mutate scope).

### Step 2: Resolve Components and Versions

1. Group **confirmed-scope** stories from Step 1.5 by component/module.
2. For each component in scope, read version from Step 0 validated version map.
3. If a component has no version entry in both Summary and config, stop and ask user.

### Step 3: Create Blank Detail Pages First

Use Confluence MCP (not local scripts for this skill) to create empty detail pages in APRN:

1. Locate parent id from `release_note_parent_pages[component]`.
2. Create page with:
   - `space_key: APRN`
   - `parent_id: <mapped parent page id>`
   - `title: <date + component + version + Release Note>`
   - `content: " "` (blank placeholder)
3. Capture each created page URL for summary links.

If parent mapping is missing, ask user and do not create that component page.

### Step 4: Generate Release Note Summary

1. Draft sections in requested style:
   - `#### <Component> V<version>`
   - grouped `For <Platform>`
   - bullet prefix decided by **Story Type** (`customfield_10085.value`):

     | Story Type                     | Bullet prefix |
     | ------------------------------ | ------------- |
     | `Improvement`                  | `- Update:`   |
     | `New Feature`                  | `- New:`      |
     | `API Integration & Enablement` | `- New:`      |

     If `customfield_10085` is missing or null on a confirmed-scope Story,
     stop and ask the user to set it in Jira (do not silently default).

2. Fill `Click [here](...)` with URLs from Step 3.
3. Return final markdown (or markdown source if requested).

### Step 4.5: Write to tmp/ for Manual Paste

This step is the **only** delivery channel for Summary content. Per the
Safety Rule above, the skill must never write to the Summary page itself.

Reasons:

1. The Summary page is shared across teams; any accidental edit affects
   everyone's release notes.
2. Current MCP only supports full-page overwrite via markdown round-trip,
   which strips Confluence smart links / inline-card macros (existing
   `Click here for details.` lines lose their URLs).

Write the generated markdown to a local file for the user to copy:

1. Compute filename from the release window:
   `tmp/<Mon>-<DD>-<YYYY> Release Note Summary.md`
   (for example `tmp/Apr-28-2026 Release Note Summary.md`).
   - Windows filenames cannot contain `/`, so use `-` as separator.
2. File body must contain a single dated section using `/` form in the heading:
   - First line: `## <Mon>/<DD>/<YYYY> Middle Platform`
   - Then one `#### <Component> V<version>` block per in-scope module,
     in the format defined in `Required Output Format`.
3. If the file already exists for the same window:
   - If section heading matches: append new module blocks at the end of the
     file, after the last `#### ...` block, without duplicating existing modules.
   - If a target module already exists in the file, ask the user whether to
     replace, merge, or skip.
4. Preserve heading levels: `##` for date section, `####` for module blocks.
5. After writing, tell the user:
   - The exact file path that was written.
   - Where to paste it in Confluence: under the matching `## <date> Middle Platform`
     section in the Summary page, or at the top of the page if the section
     does not yet exist.

This step is intentionally manual. Even when a future storage-format append
script lands under `scripts/confluence/`, any Summary write path MUST be
opt-in per run (explicit user confirmation), and the default of this skill
remains "tmp file only".

### Step 5: Update Local Component Versions

After Step 4 output is ready, update
`config/assets/project/CP/component-versions.yaml`:

1. Write back confirmed versions for involved modules.
2. Apply minimal edits only to changed module versions.
3. Do not change unrelated modules or mappings.

## Platform and Bullet Rules

- Bullet prefix is **driven by Jira `Story Type` (customfield_10085)**, not by
  the agent's prose judgement. See Step 4 mapping table.
- If a Story's type looks wrong for the change (for example `Improvement` on
  a clearly net-new feature), surface it to the user and ask whether to fix
  the Jira ticket — do not override silently in the markdown.
- Keep bullets short and user-facing.
- Keep language consistent with user request (Chinese or English).
- Do not include Jira keys in bullets unless user asks.

## Validation Checklist

Before returning:

1. Summary page version check is executed before workflow.
2. Every section version equals validated Summary versions for involved modules.
3. Every `Click [here]` URL points to a newly created page.
4. Created pages are under the mapped parent module directories.
5. `component_versions` is updated after workflow for changed involved modules.
6. Section headings and bullet styles match user template exactly.
7. `tmp/<Mon>-<DD>-<YYYY> Release Note Summary.md` is written and its path
   is returned to the user with paste instructions.
8. No write call has been made against the Summary page or any of its
   ancestors/descendants (Safety Rule).
9. Step 1.5 user confirmation was obtained; downstream steps operated only
   on the confirmed-scope subset, never on the full Sprint candidate list.
10. Every confirmed-scope Story has a non-null `customfield_10085` (Story Type),
    and bullet prefixes were derived from the Step 4 mapping table — not from
    free-form judgement.

## Quick Example

```markdown
#### My Report V1.17

For Chewy

- Update: Targeting Report supports CSV export format.

Click [here](https://pacvue-enterprise.atlassian.net/wiki/spaces/APRN/pages/123456789) for details.
```
