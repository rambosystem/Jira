#!/usr/bin/env python3
"""Preflight + assemble + create flow for Jira Story / Technical Story."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
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
from scripts.common.policy_bundle import load_policy_bundle
from scripts.common.ticket_config import load_jira_runtime_profile

ENV_PATH = REPO_ROOT / ".env"


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


def _auto_parent(
    project_key: str,
    components: list[str],
    quarter: str,
    epic_index: dict[str, dict[str, dict[str, str]]],
) -> str:
    lookup = {c.strip().lower() for c in components if c.strip()}
    quarter_upper = quarter.upper()
    project_map = epic_index.get(project_key.upper(), {})
    quarter_map = project_map.get(quarter_upper, {})
    for comp in lookup:
        key = quarter_map.get(comp)
        if key:
            return key
    return ""


def _assemble_fields(
    args: argparse.Namespace,
    defaults: dict[str, str],
    auto_parent_key: str,
    field_map: dict[str, str],
) -> dict[str, Any]:
    client_id_key = field_map["client_id"]
    fields: dict[str, Any] = {
        "project": {"key": args.project},
        "summary": args.summary.strip(),
        "issuetype": {"name": args.issue_type},
        "priority": {"name": args.priority},
        "components": [{"name": c} for c in args.components],
        client_id_key: [args.client_id or defaults["client_id"]],
    }
    if args.assignee_account_id:
        fields["assignee"] = {"id": args.assignee_account_id}
    elif defaults["assignee_account_id"]:
        fields["assignee"] = {"id": defaults["assignee_account_id"]}

    chosen_parent = args.parent or auto_parent_key
    if chosen_parent:
        fields["parent"] = {"key": chosen_parent}

    if args.issue_type == "Story":
        fields[field_map["story_type"]] = {"value": args.story_type}
        fields[field_map["ux_review_required"]] = {"value": args.ux_review_required}
        fields[field_map["ux_review_status"]] = {"value": args.ux_review_status}
    else:
        fields[field_map["technical_story_type"]] = {"value": args.technical_story_type}

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


def _validate_field_map(issue_type: str, field_map: dict[str, str]) -> None:
    required = {"client_id"}
    if issue_type == "Story":
        required.update({"story_type", "ux_review_required", "ux_review_status"})
    else:
        required.add("technical_story_type")
    missing = [k for k in required if not field_map.get(k)]
    if missing:
        raise RuntimeError(
            f"Missing policy field mapping for {issue_type}: {', '.join(sorted(missing))}"
        )


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
    parser.add_argument("--client-id", default="", help="Client ID, default from team.yaml")
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
        profile = load_jira_runtime_profile(REPO_ROOT)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    try:
        policy_bundle = load_policy_bundle(REPO_ROOT)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    bundle_default_project = (policy_bundle.get("profile") or {}).get("default_project") or ""
    args.project = (args.project or bundle_default_project or profile["default_project"]).upper()
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
    auth = basic_auth(profile["email"], token)

    try:
        defaults = ((policy_bundle.get("team_defaults") or {}).get(args.project)) or {}
        if not defaults:
            raise RuntimeError(f"No team defaults for project {args.project} in policy bundle.")
        field_map = (((policy_bundle.get("field_mappings") or {}).get(args.project) or {}).get(args.issue_type)) or {}
        if not field_map:
            raise RuntimeError(
                f"No field mapping for {args.project}/{args.issue_type} in policy bundle."
            )
        _validate_field_map(args.issue_type, field_map)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        duplicates = _search_duplicates(profile["base_url"], auth, args.project, args.issue_type, args.summary)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: duplicate preflight failed ({exc.code}): {body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Error: duplicate preflight failed (network): {exc}", file=sys.stderr)
        return 1

    auto_parent_key = ""
    if not args.parent:
        epic_index = policy_bundle.get("epic_index") or {}
        auto_parent_key = _auto_parent(args.project, args.components, args.quarter, epic_index)

    fields = _assemble_fields(args, defaults, auto_parent_key, field_map)
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
            profile["base_url"],
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
        post_check_fields = [
            "summary",
            "issuetype",
            "assignee",
            "priority",
            "components",
            "parent",
        ]
        for custom_key in field_map.values():
            if custom_key not in post_check_fields:
                post_check_fields.append(custom_key)
        fetched = jira_request(
            profile["base_url"],
            auth,
            f"/issue/{issue_key}?fields={','.join(post_check_fields)}",
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
                    profile["base_url"],
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
