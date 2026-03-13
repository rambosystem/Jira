from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from scripts.common.atlassian import basic_auth, jira_api_v3_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.ticket_config import (
    load_jira_runtime_profile,
    load_recent_epics,
    load_team_defaults,
)
from scripts.common.ticket_policy import load_issue_field_mapping
from scripts.common.ticket_schema import load_issue_schema, load_project_ticket_schema


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


def current_quarter_tag() -> str:
    now = datetime.now()
    year = str(now.year % 100).zfill(2)
    quarter = (now.month - 1) // 3 + 1
    return f"{year}Q{quarter}"


def normalize_issue_spec(raw_spec: dict[str, Any], profile: dict[str, str]) -> dict[str, Any]:
    spec = dict(raw_spec)
    spec["project"] = str(spec.get("project") or profile["default_project"]).upper()
    spec["issue_type"] = str(spec.get("issue_type") or "Story")
    spec["summary"] = str(spec.get("summary") or "").strip()
    if not spec["summary"]:
        raise RuntimeError("Issue summary is required.")

    components = spec.get("components") or []
    if isinstance(components, str):
        components = [c.strip() for c in components.split(",") if c.strip()]
    spec["components"] = [str(c).strip() for c in components if str(c).strip()]
    if not spec["components"]:
        raise RuntimeError("At least one component is required.")

    spec["description"] = str(spec.get("description") or "")
    spec["priority"] = str(spec.get("priority") or "")
    spec["assignee_account_id"] = str(spec.get("assignee_account_id") or "")
    spec["parent"] = str(spec.get("parent") or "").upper()
    spec["quarter"] = str(spec.get("quarter") or "").strip() or current_quarter_tag()
    spec["client_id"] = str(spec.get("client_id") or "")
    spec["story_type"] = str(spec.get("story_type") or "")
    spec["ux_review_required"] = str(spec.get("ux_review_required") or "")
    spec["ux_review_status"] = str(spec.get("ux_review_status") or "")
    spec["technical_story_type"] = str(spec.get("technical_story_type") or "")
    spec["allow_duplicate"] = bool(spec.get("allow_duplicate"))

    raw_link_pins = spec.get("link_pins") or spec.get("link_pin") or []
    if isinstance(raw_link_pins, str):
        raw_link_pins = [item.strip().upper() for item in raw_link_pins.split(",") if item.strip()]
    seen: set[str] = set()
    link_pins: list[str] = []
    for key in raw_link_pins:
        norm = str(key).strip().upper()
        if not re.fullmatch(r"[A-Z]+-\d+", norm):
            raise RuntimeError("link_pins must be Jira issue keys, e.g. PIN-2712.")
        if norm in seen:
            continue
        seen.add(norm)
        link_pins.append(norm)
    spec["link_pins"] = link_pins
    return spec


def _normalize_keyword(summary: str) -> str:
    text = re.sub(r"[\[\]锛堬級(){}\-_/]+", " ", summary)
    text = re.sub(r"\s+", " ", text).strip()
    parts = text.split(" ")
    return " ".join(parts[:8]) if parts else summary.strip()


def _escape_jql_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def search_duplicates(base_url: str, auth: str, project_key: str, issue_type: str, summary: str) -> list[dict[str, Any]]:
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


def auto_parent(repo_root: Path, project_key: str, components: list[str], quarter: str) -> str:
    project_prefix = f"{project_key.upper()}-"
    lookup = {c.strip().lower() for c in components if c.strip()}
    quarter_upper = quarter.upper()
    for epic in load_recent_epics(repo_root):
        key = str(epic.get("key", ""))
        title = str(epic.get("title", ""))
        epic_components = [str(c).strip().lower() for c in (epic.get("components") or [])]
        if not key.startswith(project_prefix):
            continue
        if quarter_upper not in title.upper():
            continue
        if lookup.intersection(epic_components):
            return key
    return ""


def option_values(issue_schema: dict[str, Any], field_name: str) -> list[str]:
    options = ((issue_schema.get("field_options") or {}).get(field_name)) or []
    return [str(item) for item in options]


def default_value(issue_schema: dict[str, Any], field_name: str) -> str:
    defaults = issue_schema.get("field_defaults") or {}
    value = defaults.get(field_name)
    return str(value) if value is not None else ""


def normalize_issue_defaults(spec: dict[str, Any], issue_schema: dict[str, Any]) -> None:
    if not spec["priority"]:
        spec["priority"] = "Medium"

    if spec["issue_type"] == "Story":
        spec["story_type"] = spec["story_type"] or default_value(issue_schema, "Story Type")
        spec["ux_review_required"] = spec["ux_review_required"] or default_value(issue_schema, "UX Review Required?")
        spec["ux_review_status"] = spec["ux_review_status"] or default_value(issue_schema, "UX Review Status")
    else:
        defaults = issue_schema.get("field_defaults") or {}
        spec["technical_story_type"] = spec["technical_story_type"] or str(defaults.get("Technical Story Type") or "Code Quality")


def validate_field_map(issue_type: str, field_map: dict[str, str]) -> None:
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


def validate_issue_spec(spec: dict[str, Any], project_schema: dict[str, Any], issue_schema: dict[str, Any]) -> None:
    supported_work_types = {str(item) for item in (project_schema.get("supported_work_types") or [])}
    if supported_work_types and spec["issue_type"] not in supported_work_types:
        raise RuntimeError(
            f"Issue type '{spec['issue_type']}' is not enabled for project {spec['project']} in ticket schema."
        )

    priority_options = option_values(issue_schema, "Priority")
    if priority_options and spec["priority"] not in priority_options:
        raise RuntimeError(f"Invalid priority '{spec['priority']}'. Allowed: {', '.join(priority_options)}")

    if spec["issue_type"] == "Story":
        story_type_options = option_values(issue_schema, "Story Type")
        if story_type_options and spec["story_type"] not in story_type_options:
            raise RuntimeError(f"Invalid story type '{spec['story_type']}'. Allowed: {', '.join(story_type_options)}")
        ux_required_options = option_values(issue_schema, "UX Review Required?")
        if ux_required_options and spec["ux_review_required"] not in ux_required_options:
            raise RuntimeError(
                f"Invalid UX review required value '{spec['ux_review_required']}'. Allowed: {', '.join(ux_required_options)}"
            )
        ux_status_options = option_values(issue_schema, "UX Review Status")
        if ux_status_options and spec["ux_review_status"] not in ux_status_options:
            raise RuntimeError(
                f"Invalid UX review status '{spec['ux_review_status']}'. Allowed: {', '.join(ux_status_options)}"
            )
    else:
        technical_story_type_options = option_values(issue_schema, "Technical Story Type")
        if technical_story_type_options and spec["technical_story_type"] not in technical_story_type_options:
            raise RuntimeError(
                "Invalid technical story type "
                f"'{spec['technical_story_type']}'. Allowed: {', '.join(technical_story_type_options)}"
            )


def assemble_fields(spec: dict[str, Any], defaults: dict[str, str], auto_parent_key: str, field_map: dict[str, str]) -> dict[str, Any]:
    client_id_key = field_map["client_id"]
    fields: dict[str, Any] = {
        "project": {"key": spec["project"]},
        "summary": spec["summary"],
        "issuetype": {"name": spec["issue_type"]},
        "priority": {"name": spec["priority"]},
        "components": [{"name": c} for c in spec["components"]],
        client_id_key: [spec["client_id"] or defaults["client_id"]],
    }
    if spec["assignee_account_id"]:
        fields["assignee"] = {"id": spec["assignee_account_id"]}
    elif defaults["assignee_account_id"]:
        fields["assignee"] = {"id": defaults["assignee_account_id"]}

    chosen_parent = spec["parent"] or auto_parent_key
    if chosen_parent:
        fields["parent"] = {"key": chosen_parent}

    if spec["issue_type"] == "Story":
        fields[field_map["story_type"]] = {"value": spec["story_type"]}
        fields[field_map["ux_review_required"]] = {"value": spec["ux_review_required"]}
        fields[field_map["ux_review_status"]] = {"value": spec["ux_review_status"]}
    else:
        fields[field_map["technical_story_type"]] = {"value": spec["technical_story_type"]}

    if spec["description"]:
        fields["description"] = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": spec["description"]}],
                }
            ],
        }

    return fields


def assemble_issue_plan(repo_root: Path, env_path: Path, raw_spec: dict[str, Any], *, check_duplicates: bool = True) -> dict[str, Any]:
    load_dotenv(env_path)
    profile = load_jira_runtime_profile(repo_root)
    spec = normalize_issue_spec(raw_spec, profile)

    token = load_token()
    auth = basic_auth(profile["email"], token)

    defaults = load_team_defaults(repo_root, spec["project"])
    project_schema = load_project_ticket_schema(repo_root, spec["project"])
    issue_schema = load_issue_schema(repo_root, spec["project"], spec["issue_type"])
    normalize_issue_defaults(spec, issue_schema)
    validate_issue_spec(spec, project_schema, issue_schema)
    field_map = load_issue_field_mapping(repo_root, spec["project"], spec["issue_type"])
    validate_field_map(spec["issue_type"], field_map)

    duplicate_check_error = ""
    duplicates: list[dict[str, Any]] = []
    if check_duplicates:
        try:
            duplicates = search_duplicates(profile["base_url"], auth, spec["project"], spec["issue_type"], spec["summary"])
        except HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            duplicate_check_error = f"duplicate preflight failed ({exc.code}): {body}"
        except URLError as exc:
            duplicate_check_error = f"duplicate preflight failed (network): {exc}"

    auto_parent_key = ""
    if not spec["parent"]:
        auto_parent_key = auto_parent(repo_root, spec["project"], spec["components"], spec["quarter"])

    fields = assemble_fields(spec, defaults, auto_parent_key, field_map)
    duplicate_brief = [
        {
            "key": issue.get("key"),
            "summary": issue.get("fields", {}).get("summary", ""),
            "status": (issue.get("fields", {}).get("status") or {}).get("name", ""),
        }
        for issue in duplicates
    ]
    preflight = {
        "project": spec["project"],
        "issue_type": spec["issue_type"],
        "quarter": spec["quarter"],
        "auto_parent": auto_parent_key,
        "resolved_parent": (fields.get("parent") or {}).get("key", ""),
        "duplicate_count": len(duplicates),
        "duplicates": duplicate_brief,
    }
    if duplicate_check_error:
        preflight["duplicate_check_error"] = duplicate_check_error

    return {
        "profile": {
            "base_url": profile["base_url"],
            "email": profile["email"],
        },
        "spec": spec,
        "preflight": preflight,
        "payload": {"fields": fields},
        "link_plan": {
            "type": "Relates",
            "outward_issues": spec["link_pins"],
        } if spec["link_pins"] else None,
        "field_map": field_map,
    }


def execute_issue_plan(plan: dict[str, Any], token: str, *, fetch_post_check: bool = True) -> dict[str, Any]:
    profile = plan["profile"]
    fields = ((plan.get("payload") or {}).get("fields")) or {}
    if not fields:
        raise RuntimeError("Plan payload.fields is required.")

    auth = basic_auth(str(profile["email"]), token)
    created = jira_request(
        str(profile["base_url"]),
        auth,
        "/issue",
        method="POST",
        data={"fields": fields},
    )
    issue_key = created.get("key", "")
    if not issue_key:
        raise RuntimeError("Jira create response has no issue key.")

    out: dict[str, Any] = {
        "preflight": plan.get("preflight") or {},
        "created": created,
    }

    if fetch_post_check:
        post_check_fields = ["summary", "issuetype", "assignee", "priority", "components", "parent"]
        for custom_key in (plan.get("field_map") or {}).values():
            if custom_key not in post_check_fields:
                post_check_fields.append(custom_key)
        fetched = jira_request(
            str(profile["base_url"]),
            auth,
            f"/issue/{issue_key}?fields={','.join(post_check_fields)}",
            method="GET",
        )
        out["post_check"] = {
            "key": issue_key,
            "summary": fetched.get("fields", {}).get("summary", ""),
            "issue_type": (fetched.get("fields", {}).get("issuetype") or {}).get("name", ""),
            "assignee_account_id": (fetched.get("fields", {}).get("assignee") or {}).get("accountId", ""),
            "priority": (fetched.get("fields", {}).get("priority") or {}).get("name", ""),
            "components": [c.get("name") for c in fetched.get("fields", {}).get("components", [])],
            "parent": (fetched.get("fields", {}).get("parent") or {}).get("key", ""),
        }

    link_plan = plan.get("link_plan") or {}
    link_targets = link_plan.get("outward_issues") or []
    if link_targets:
        link_results: list[dict[str, Any]] = []
        has_failures = False
        for pin_key in link_targets:
            try:
                link_resp = jira_request(
                    str(profile["base_url"]),
                    auth,
                    "/issueLink",
                    method="POST",
                    data={
                        "type": {"name": str(link_plan.get("type") or "Relates")},
                        "inwardIssue": {"key": issue_key},
                        "outwardIssue": {"key": pin_key},
                    },
                )
                link_results.append(
                    {
                        "requested": pin_key,
                        "link_type": str(link_plan.get("type") or "Relates"),
                        "status": "linked",
                        "response": link_resp,
                    }
                )
            except HTTPError as exc:
                body = exc.read().decode("utf-8") if exc.fp else ""
                link_results.append(
                    {
                        "requested": pin_key,
                        "link_type": str(link_plan.get("type") or "Relates"),
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
                        "link_type": str(link_plan.get("type") or "Relates"),
                        "status": "failed",
                        "error": f"network error: {exc}",
                    }
                )
                has_failures = True
        out["pin_links"] = link_results
        out["pin_link_failures"] = has_failures

    return out


def resolve_output_path(repo_root: Path, output_file: str) -> Path | None:
    if not output_file:
        return None
    out_path = Path(output_file)
    if not out_path.is_absolute():
        out_path = repo_root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def write_output(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_token() -> str:
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("ATLASSIAN_API_TOKEN not set.")
    return token
