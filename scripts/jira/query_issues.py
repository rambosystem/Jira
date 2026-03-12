#!/usr/bin/env python3
"""Query Jira issues using project query presets."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth, jira_api_v3_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.ticket_config import load_jira_runtime_profile

ENV_PATH = REPO_ROOT / ".env"


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _project_paths(project: str) -> tuple[Path, Path, Path]:
    root = REPO_ROOT / "assets" / "project" / project.upper()
    return (
        root / "query-templates.yaml",
        root / "team.yaml",
        root / "components.yaml",
    )


def _extract_preset_block(text: str, preset: str) -> str:
    m = re.search(
        rf"(?ms)^{re.escape(preset)}:\n(.*?)(?=^[A-Za-z0-9_]+:\n|\Z)",
        text,
    )
    if not m:
        raise RuntimeError(f"Preset '{preset}' not found in query templates.")
    return m.group(1)


def _extract_jql_template(block: str) -> str:
    m = re.search(r"(?ms)^\s{2}jql_template:\s*\|\n(.*?)(?=^\s{2}[A-Za-z0-9_-]+:\s|\Z)", block)
    if not m:
        raise RuntimeError("Preset missing jql_template.")
    return textwrap.dedent(m.group(1)).strip()


def _extract_default_order(block: str) -> str:
    m = re.search(r'(?m)^\s{4}order:\s*"([^"]+)"\s*$', block)
    if m:
        return m.group(1).strip()
    return "ORDER BY created DESC"


def _extract_project_key(team_text: str) -> str:
    m = re.search(r'(?ms)^\s*workspace:\s*\n.*?^\s*project:\s*\n.*?^\s*key:\s*([A-Za-z0-9_]+)\s*$', team_text)
    return m.group(1).strip().upper() if m else ""


def _extract_issue_types(team_text: str) -> list[str]:
    m = re.search(r"(?ms)^\s*ticketing:\s*\n.*?^\s*supported_work_types:\s*\n(.*?)(?=^\s*\w)", team_text)
    if not m:
        return ["Story", "Technical Story", "Bug", "Epic"]
    lines = m.group(1).splitlines()
    out: list[str] = []
    for line in lines:
        mm = re.match(r"^\s*-\s*(.+?)\s*$", line)
        if not mm:
            continue
        out.append(mm.group(1).strip().strip('"').strip("'"))
    return out or ["Story", "Technical Story", "Bug", "Epic"]


def _extract_account_ids(team_text: str) -> list[str]:
    ids = re.findall(r'(?m)^\s*account_id:\s*["\']?([^"\n\']+)["\']?\s*$', team_text)
    seen: set[str] = set()
    out: list[str] = []
    for account_id in ids:
        if account_id in seen:
            continue
        seen.add(account_id)
        out.append(account_id)
    return out


def _extract_components(components_text: str) -> list[str]:
    names = re.findall(r'(?m)^\s*-\s*name:\s*(.+?)\s*$', components_text)
    out: list[str] = []
    for name in names:
        out.append(name.strip().strip('"').strip("'"))
    return out


def _quote_list(values: list[str]) -> str:
    safe = [v.replace('"', '\\"') for v in values if v]
    return ", ".join(f'"{v}"' for v in safe)


def _render_template(template: str, vars_map: dict[str, str]) -> str:
    rendered = template
    for key, value in vars_map.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    # Collapse any unreplaced placeholders to empty to avoid broken JQL fragments.
    rendered = re.sub(r"\{\{[A-Za-z0-9_]+\}\}", "", rendered)
    return "\n".join(line.rstrip() for line in rendered.splitlines()).strip()


def _search_jira(base_url: str, auth: str, jql: str, fields: list[str], limit: int) -> dict[str, Any]:
    url = jira_api_v3_url(base_url, "/search/jql")
    payload = {"jql": jql, "maxResults": limit, "fields": fields}
    return request_json(
        url,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        data=payload,
        insecure_env_var="JIRA_INSECURE_SSL",
    )


def _table_rows(issues: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for issue in issues:
        fields = issue.get("fields") or {}
        rows.append(
            {
                "key": issue.get("key", ""),
                "status": (fields.get("status") or {}).get("name", ""),
                "assignee": (fields.get("assignee") or {}).get("displayName", ""),
                "priority": (fields.get("priority") or {}).get("name", ""),
                "summary": fields.get("summary", ""),
            }
        )
    return rows


def _print_table(rows: list[dict[str, str]]) -> None:
    headers = ["key", "status", "assignee", "priority", "summary"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(row.get(h, "")))
    line = " | ".join(h.ljust(widths[h]) for h in headers)
    sep = "-+-".join("-" * widths[h] for h in headers)
    print(line)
    print(sep)
    for row in rows:
        print(" | ".join(row.get(h, "").ljust(widths[h]) for h in headers))


def run() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Query Jira by preset templates.")
    parser.add_argument("--project", default="", help="Project key. Defaults to profile default_project.")
    parser.add_argument(
        "--preset",
        default="team_board",
        choices=["team_board", "sprint_done_stories", "duplicate_check"],
        help="Query preset. Use --jql to bypass presets.",
    )
    parser.add_argument("--jql", default="", help="Raw JQL override. If set, preset/template is ignored.")
    parser.add_argument("--sprint-name", default="", help="Required for sprint_done_stories preset.")
    parser.add_argument("--summary", default="", help="Used by duplicate_check preset.")
    parser.add_argument("--issue-type", default="Story", help='Used by duplicate_check preset, e.g. "Story".')
    parser.add_argument("--keyword", default="", help='Optional: append `AND summary ~ "<keyword>"`.')
    parser.add_argument("--issue-types", default="", help='Comma-separated issue types override.')
    parser.add_argument("--assignee-ids", default="", help="Comma-separated assignee account ids override.")
    parser.add_argument("--reporter-id", default="", help="Reporter account id override.")
    parser.add_argument("--components", default="", help="Comma-separated components override.")
    parser.add_argument("--order", default="", help='Override order clause, e.g. "ORDER BY updated DESC".')
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--fields",
        default="key,summary,status,assignee,priority,components,parent,created",
        help="Comma-separated Jira fields.",
    )
    parser.add_argument("--format", default="table", choices=["table", "json"])
    parser.add_argument("--dry-run", action="store_true", help="Print rendered JQL and vars, no Jira request.")
    args = parser.parse_args()

    try:
        profile = load_jira_runtime_profile(REPO_ROOT)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    project = (args.project or profile["default_project"]).upper()
    qpath, tpath, cpath = _project_paths(project)
    if args.jql.strip():
        query_text = ""
        team_text = _read_text(tpath) if tpath.is_file() else ""
        components_text = cpath.read_text(encoding="utf-8") if cpath.is_file() else ""
        block = ""
        jql_template = ""
    else:
        try:
            query_text = _read_text(qpath)
            team_text = _read_text(tpath)
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        components_text = cpath.read_text(encoding="utf-8") if cpath.is_file() else ""
        if args.preset == "duplicate_check":
            jql_template = (
                "project = {{project}}\n"
                "AND issuetype = \"{{issue_type}}\"\n"
                "AND summary ~ \"\\\"{{summary_keyword}}\\\"\"\n"
                "ORDER BY created DESC"
            )
            block = ""
        else:
            try:
                block = _extract_preset_block(query_text, args.preset)
                jql_template = _extract_jql_template(block)
            except RuntimeError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1

    default_project_from_team = _extract_project_key(team_text) or project
    issue_types = (
        [x.strip() for x in args.issue_types.split(",") if x.strip()]
        if args.issue_types
        else _extract_issue_types(team_text)
    )
    assignee_ids = (
        [x.strip() for x in args.assignee_ids.split(",") if x.strip()]
        if args.assignee_ids
        else _extract_account_ids(team_text)
    )
    reporter_id = args.reporter_id.strip() or profile["account_id"]
    components = (
        [x.strip() for x in args.components.split(",") if x.strip()]
        if args.components
        else _extract_components(components_text)
    )
    order = args.order.strip() or (_extract_default_order(block) if block else "ORDER BY created DESC")
    summary_keyword = re.sub(r"[\[\]（）(){}\-_/]+", " ", args.summary).strip()
    summary_keyword = re.sub(r"\s+", " ", summary_keyword)
    if summary_keyword:
        summary_keyword = " ".join(summary_keyword.split(" ")[:8])

    vars_map = {
        "project": default_project_from_team,
        "issue_types": _quote_list(issue_types),
        "assignee_ids": _quote_list(assignee_ids),
        "reporter_id": f'"{reporter_id}"',
        "components": _quote_list(components),
        "order": order,
        "sprint_name": args.sprint_name.strip(),
        "issue_type": args.issue_type.strip(),
        "summary_keyword": summary_keyword.replace("\\", "\\\\").replace('"', '\\"'),
    }
    if args.jql.strip():
        jql = args.jql.strip()
    else:
        jql = _render_template(jql_template, vars_map)
    if args.preset == "sprint_done_stories" and not args.sprint_name.strip() and not args.jql.strip():
        print("Error: --sprint-name is required for sprint_done_stories.", file=sys.stderr)
        return 1
    if args.preset == "duplicate_check" and not args.summary.strip() and not args.jql.strip():
        print("Error: --summary is required for duplicate_check preset.", file=sys.stderr)
        return 1
    if args.keyword.strip():
        kw = args.keyword.replace("\\", "\\\\").replace('"', '\\"')
        jql = f"({jql})\nAND summary ~ \"{kw}\""
    if order and "ORDER BY" in order.upper() and "ORDER BY" not in jql.upper():
        jql = f"{jql}\n{order}"

    if args.dry_run:
        print(
            json.dumps(
                {
                    "project": project,
                    "preset": args.preset,
                    "vars": vars_map,
                    "jql": jql,
                    "limit": args.limit,
                    "fields": [f.strip() for f in args.fields.split(",") if f.strip()],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("Error: ATLASSIAN_API_TOKEN not set.", file=sys.stderr)
        return 1
    auth = basic_auth(profile["email"], token)
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    try:
        data = _search_jira(profile["base_url"], auth, jql, fields, max(1, min(args.limit, 100)))
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: Jira query failed ({exc.code}): {body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Error: Jira query failed (network): {exc}", file=sys.stderr)
        return 1

    issues = data.get("issues") or []
    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        rows = _table_rows(issues)
        _print_table(rows)
        print(f"\nTotal: {len(issues)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
