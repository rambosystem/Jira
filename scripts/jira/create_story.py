#!/usr/bin/env python3
"""Preflight + assemble + create flow for Jira Story / Technical Story."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
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

ENV_PATH = REPO_ROOT / ".env"
PROFILE_PATH = REPO_ROOT / "assets" / "global" / "profile.yaml"
EPIC_LIST_PATH = REPO_ROOT / "assets" / "global" / "epic-list.yaml"


@dataclass
class Profile:
    base_url: str
    email: str
    account_id: str
    default_project: str


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _yaml_scalar(text: str, key: str) -> str:
    m = re.search(
        rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'#\n]+)[\"']?\s*(?:#|$)",
        text,
        re.MULTILINE,
    )
    return m.group(1).strip() if m else ""


def _load_profile() -> Profile:
    text = _read_text(PROFILE_PATH)
    base_url = _yaml_scalar(text, "confluence_base_url").rstrip("/")
    email = _yaml_scalar(text, "email")
    account_id = _yaml_scalar(text, "account_id")
    default_project = _yaml_scalar(text, "default_project") or "CP"
    if not base_url:
        raise RuntimeError("Missing confluence_base_url in profile.")
    if not email:
        raise RuntimeError("Missing email in profile.")
    if not account_id:
        raise RuntimeError("Missing account_id in profile.")
    return Profile(
        base_url=base_url,
        email=email,
        account_id=account_id,
        default_project=default_project,
    )


def _project_team_path(project_key: str) -> Path:
    return REPO_ROOT / "assets" / "project" / project_key.upper() / "team.yaml"


def _load_team_defaults(project_key: str) -> dict[str, str]:
    path = _project_team_path(project_key)
    text = _read_text(path)

    client_id = _yaml_scalar(text, "client_id") or "0000"
    assignee = _yaml_scalar(text, "default_assignee_account_id")
    if not assignee:
        m = re.search(
            r"(?ms)^\s*defaults:\s*\n.*?^\s*assignee:\s*\n.*?^\s*account_id:\s*[\"']?([^\"'\n#]+)",
            text,
        )
        assignee = m.group(1).strip() if m else ""
    return {
        "client_id": client_id,
        "assignee_account_id": assignee,
    }


def _current_quarter_tag() -> str:
    now = datetime.now()
    year = str(now.year % 100).zfill(2)
    quarter = (now.month - 1) // 3 + 1
    return f"{year}Q{quarter}"


def _normalize_keyword(summary: str) -> str:
    text = re.sub(r"[\[\]（）(){}\-_/]+", " ", summary)
    text = re.sub(r"\s+", " ", text).strip()
    parts = text.split(" ")
    return " ".join(parts[:8]) if parts else summary.strip()


def _escape_jql_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def jira_request(base_url: str, auth: str, path: str, *, method: str = "GET", data: dict[str, Any] | None = None) -> Any:
    url = jira_api_v3_url(base_url, path)
    return request_json(
        url,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        data=data,
        insecure_env_var="JIRA_INSECURE_SSL",
    )


def _search_duplicates(base_url: str, auth: str, project_key: str, issue_type: str, summary: str) -> list[dict[str, Any]]:
    keyword = _normalize_keyword(summary)
    phrase = _escape_jql_literal(keyword)
    jql = (
        f"project = {project_key} "
        f'AND issuetype = "{issue_type}" '
        f'AND summary ~ "\\"{phrase}\\"" '
        "ORDER BY created DESC"
    )
    data = jira_request(
        base_url,
        auth,
        "/search/jql",
        method="POST",
        data={
            "jql": jql,
            "maxResults": 5,
            "fields": ["key", "summary", "status", "parent"],
        },
    )
    return data.get("issues") or []


def _parse_epics() -> list[dict[str, Any]]:
    text = _read_text(EPIC_LIST_PATH)
    lines = text.splitlines()
    in_recent = False
    epics: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in lines:
        if not in_recent:
            if re.match(r"^\s*recent_epics:\s*$", line):
                in_recent = True
            continue
        if in_recent and re.match(r"^\S", line):
            break
        m_key = re.match(r"^\s*-\s*key:\s*([A-Z]+-\d+)\s*$", line)
        if m_key:
            if current:
                epics.append(current)
            current = {"key": m_key.group(1), "title": "", "components": []}
            continue
        if current is None:
            continue
        m_title = re.match(r"^\s*title:\s*(.+?)\s*$", line)
        if m_title:
            current["title"] = m_title.group(1).strip().strip('"').strip("'")
            continue
        m_comps = re.match(r"^\s*components:\s*\[(.*)\]\s*$", line)
        if m_comps:
            raw = m_comps.group(1).strip()
            if not raw:
                current["components"] = []
            else:
                current["components"] = [c.strip().strip('"').strip("'") for c in raw.split(",") if c.strip()]
    if current:
        epics.append(current)
    return epics


def _auto_parent(project_key: str, components: list[str], quarter: str) -> str:
    project_prefix = f"{project_key.upper()}-"
    lookup = {c.strip().lower() for c in components if c.strip()}
    quarter_upper = quarter.upper()
    for epic in _parse_epics():
        key = epic.get("key", "")
        title = str(epic.get("title", ""))
        epic_components = [str(c).strip().lower() for c in epic.get("components", [])]
        if not key.startswith(project_prefix):
            continue
        if quarter_upper not in title.upper():
            continue
        if lookup.intersection(epic_components):
            return key
    return ""


def _assemble_fields(args: argparse.Namespace, defaults: dict[str, str], auto_parent_key: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "project": {"key": args.project},
        "summary": args.summary.strip(),
        "issuetype": {"name": args.issue_type},
        "priority": {"name": args.priority},
        "components": [{"name": c} for c in args.components],
        "customfield_10043": [args.client_id or defaults["client_id"]],
    }
    if args.assignee_account_id:
        fields["assignee"] = {"id": args.assignee_account_id}
    elif defaults["assignee_account_id"]:
        fields["assignee"] = {"id": defaults["assignee_account_id"]}

    chosen_parent = args.parent or auto_parent_key
    if chosen_parent:
        fields["parent"] = {"key": chosen_parent}

    if args.issue_type == "Story":
        fields["customfield_10085"] = {"value": args.story_type}
        fields["customfield_13319"] = {"value": args.ux_review_required}
        fields["customfield_13320"] = {"value": args.ux_review_status}
    else:
        fields["customfield_12348"] = {"value": args.technical_story_type}

    if args.description:
        fields["description"] = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": args.description}],
                }
            ],
        }

    return fields


def run() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(
        description="Create Jira Story/Technical Story with preflight checks and auto field assembly.",
    )
    parser.add_argument("--project", default="", help="Project key, default from assets/global/profile.yaml")
    parser.add_argument("--issue-type", default="Story", choices=["Story", "Technical Story"])
    parser.add_argument("--summary", required=True, help="Issue summary/title")
    parser.add_argument("--components", required=True, help="Comma-separated components, e.g. 'SOV,My Report'")
    parser.add_argument("--description", default="", help="Plain text description")
    parser.add_argument("--priority", default="Medium")
    parser.add_argument("--assignee-account-id", default="", help="Atlassian account id")
    parser.add_argument("--parent", default="", help="Parent issue key override, e.g. CP-45460")
    parser.add_argument("--quarter", default="", help="Quarter token for auto parent match, e.g. 26Q2")
    parser.add_argument("--client-id", default="", help="Client ID for customfield_10043, default from team.yaml")
    parser.add_argument("--story-type", default="Improvement")
    parser.add_argument("--ux-review-required", default="No", choices=["Yes", "No"])
    parser.add_argument("--ux-review-status", default="Not Needed", choices=["Not Needed", "Pending", "Reviewed"])
    parser.add_argument("--technical-story-type", default="Code Quality")
    parser.add_argument("--allow-duplicate", action="store_true", help="Create even if similar summary exists")
    parser.add_argument(
        "--link-pin",
        default="",
        help="PIN issue keys to link after create, comma-separated allowed, e.g. PIN-2712,PIN-2805",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only run preflight and print payload")
    args = parser.parse_args()

    try:
        profile = _load_profile()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    args.project = (args.project or profile.default_project).upper()
    args.components = [c.strip() for c in args.components.split(",") if c.strip()]
    if not args.components:
        print("Error: --components must include at least one component.", file=sys.stderr)
        return 1
    args.quarter = args.quarter.strip() or _current_quarter_tag()
    raw_link_pins: list[str] = [item.strip().upper() for item in args.link_pin.split(",") if item.strip()]
    seen: set[str] = set()
    link_pins: list[str] = []
    for key in raw_link_pins:
        if not re.fullmatch(r"[A-Z]+-\d+", key):
            print("Error: --link-pin must be issue key(s), e.g. PIN-2712 or PIN-1,PIN-2.", file=sys.stderr)
            return 1
        if key in seen:
            continue
        seen.add(key)
        link_pins.append(key)

    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("Error: ATLASSIAN_API_TOKEN not set.", file=sys.stderr)
        return 1
    auth = basic_auth(profile.email, token)

    try:
        defaults = _load_team_defaults(args.project)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        duplicates = _search_duplicates(profile.base_url, auth, args.project, args.issue_type, args.summary)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: duplicate preflight failed ({exc.code}): {body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Error: duplicate preflight failed (network): {exc}", file=sys.stderr)
        return 1

    auto_parent_key = ""
    if not args.parent:
        auto_parent_key = _auto_parent(args.project, args.components, args.quarter)

    fields = _assemble_fields(args, defaults, auto_parent_key)
    duplicate_brief = [
        {
            "key": issue.get("key"),
            "summary": issue.get("fields", {}).get("summary", ""),
            "status": (issue.get("fields", {}).get("status") or {}).get("name", ""),
        }
        for issue in duplicates
    ]

    preflight = {
        "project": args.project,
        "issue_type": args.issue_type,
        "quarter": args.quarter,
        "auto_parent": auto_parent_key,
        "resolved_parent": (fields.get("parent") or {}).get("key", ""),
        "duplicate_count": len(duplicates),
        "duplicates": duplicate_brief,
    }

    if duplicates and not args.allow_duplicate:
        print(json.dumps({"preflight": preflight, "blocked": "duplicate_detected"}, ensure_ascii=False, indent=2))
        print("Hint: pass --allow-duplicate to continue.", file=sys.stderr)
        return 2

    if args.dry_run:
        dry = {"preflight": preflight, "payload": {"fields": fields}}
        if link_pins:
            dry["link_plan"] = {
                "type": "Relates",
                "inward_issue": "(new issue key after create)",
                "outward_issues": link_pins,
            }
        print(json.dumps(dry, ensure_ascii=False, indent=2))
        return 0

    try:
        created = jira_request(
            profile.base_url,
            auth,
            "/issue",
            method="POST",
            data={"fields": fields},
        )
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(
            json.dumps(
                {
                    "preflight": preflight,
                    "payload": {"fields": fields},
                    "error_code": exc.code,
                    "error_body": body,
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    except URLError as exc:
        print(
            json.dumps(
                {
                    "preflight": preflight,
                    "payload": {"fields": fields},
                    "error": f"create failed (network): {exc}",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    issue_key = created.get("key", "")
    if not issue_key:
        print(json.dumps({"preflight": preflight, "created": created}, ensure_ascii=False, indent=2))
        print("Error: Jira create response has no issue key.", file=sys.stderr)
        return 1

    try:
        fetched = jira_request(
            profile.base_url,
            auth,
            f"/issue/{issue_key}?fields=summary,issuetype,assignee,priority,components,parent,customfield_10043,customfield_10085,customfield_12348,customfield_13319,customfield_13320",
            method="GET",
        )
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(
            json.dumps(
                {
                    "preflight": preflight,
                    "created": created,
                    "post_check_error_code": exc.code,
                    "post_check_error_body": body,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    except URLError as exc:
        print(
            json.dumps(
                {
                    "preflight": preflight,
                    "created": created,
                    "post_check_error": f"network error: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    out = {
        "preflight": preflight,
        "created": created,
        "post_check": {
            "key": issue_key,
            "summary": fetched.get("fields", {}).get("summary", ""),
            "issue_type": (fetched.get("fields", {}).get("issuetype") or {}).get("name", ""),
            "assignee_account_id": (fetched.get("fields", {}).get("assignee") or {}).get("accountId", ""),
            "priority": (fetched.get("fields", {}).get("priority") or {}).get("name", ""),
            "components": [c.get("name") for c in fetched.get("fields", {}).get("components", [])],
            "parent": (fetched.get("fields", {}).get("parent") or {}).get("key", ""),
        },
    }

    if link_pins:
        link_results: list[dict[str, Any]] = []
        has_failures = False
        for pin_key in link_pins:
            try:
                link_resp = jira_request(
                    profile.base_url,
                    auth,
                    "/issueLink",
                    method="POST",
                    data={
                        "type": {"name": "Relates"},
                        "inwardIssue": {"key": issue_key},
                        "outwardIssue": {"key": pin_key},
                    },
                )
                link_results.append(
                    {
                        "requested": pin_key,
                        "link_type": "Relates",
                        "status": "linked",
                        "response": link_resp,
                    }
                )
            except HTTPError as exc:
                body = exc.read().decode("utf-8") if exc.fp else ""
                link_results.append(
                    {
                        "requested": pin_key,
                        "link_type": "Relates",
                        "status": "failed",
                        "error_code": exc.code,
                        "error_body": body,
                    }
                )
                has_failures = True
            except URLError as exc:
                link_results.append(
                    {
                        "requested": pin_key,
                        "link_type": "Relates",
                        "status": "failed",
                        "error": f"network error: {exc}",
                    }
                )
                has_failures = True
        out["pin_links"] = link_results
        if has_failures:
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(run())
