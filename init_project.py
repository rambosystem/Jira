#!/usr/bin/env python3
from __future__ import annotations

import base64
import getpass
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from scripts.common.http import ssl_context


ATLASSIAN_BASE_URL = "https://pacvue-enterprise.atlassian.net"
REPO_ROOT = Path(__file__).resolve().parent
PROFILE_PATH = REPO_ROOT / "config" / "assets" / "global" / "profile.yaml"
ENV_PATH = REPO_ROOT / ".env"


def log(message: str) -> None:
    print(f"[init] {message}")


def fail(message: str) -> None:
    print(f"[init][error] {message}", file=sys.stderr)


def debug_enabled() -> bool:
    return os.environ.get("DEBUG_INIT", "").strip() == "1"


def debug(message: str) -> None:
    if debug_enabled():
        print(f"[init][debug] {message}")


def is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def prompt_non_empty(label: str, secret: bool = False) -> str:
    while True:
        value = getpass.getpass(label) if secret else input(label)
        value = value.strip()
        if value:
            return value
        fail(f"{label.rstrip(': ')} cannot be empty.")


def prompt_email() -> str:
    while True:
        value = prompt_non_empty("Input email: ")
        if is_valid_email(value):
            return value
        fail("Invalid email format. Please retry.")


def basic_auth(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def api_request(
    url: str,
    auth_b64: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {auth_b64}",
    }
    payload = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    debug(f"{method} {url}")
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)

    insecure_env_var = "CONFLUENCE_INSECURE_SSL" if "/wiki/" in url else "JIRA_INSECURE_SSL"
    ctx = ssl_context(insecure_env_var)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, context=ctx) as resp:
                body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
        except URLError as exc:
            last_error = exc
            message = str(exc.reason if getattr(exc, "reason", None) else exc)
            is_tls_eof = "UNEXPECTED_EOF_WHILE_READING" in message or "EOF occurred in violation of protocol" in message
            if attempt == 0 and is_tls_eof:
                debug(f"Retrying after TLS EOF: {url}")
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError(f"Unexpected request failure: {url}")


def get_json(path: str, auth_b64: str) -> Any:
    return api_request(f"{ATLASSIAN_BASE_URL.rstrip('/')}{path}", auth_b64)


def post_json(path: str, auth_b64: str, data: dict[str, Any]) -> Any:
    return api_request(f"{ATLASSIAN_BASE_URL.rstrip('/')}{path}", auth_b64, method="POST", data=data)


def derive_username(email: str, display_name: str) -> str:
    local = email.split("@", 1)[0] if "@" in email else email
    candidate = local or display_name or "user"
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-")
    return candidate or "user"


def validate_identity(email: str, token: str) -> dict[str, str]:
    auth_b64 = basic_auth(email, token)
    log("Fetching Atlassian identity from /rest/api/3/myself")
    myself = get_json("/rest/api/3/myself", auth_b64)
    account_id = str(myself.get("accountId") or "")
    display_name = str(myself.get("displayName") or "")
    if not account_id:
        raise RuntimeError("account_id missing from /rest/api/3/myself")
    return {
        "auth_b64": auth_b64,
        "account_id": account_id,
        "display_name": display_name,
    }


def resolve_default_workspace(auth_b64: str, account_id: str) -> dict[str, str]:
    log("Resolving Confluence workspace")
    space_key = ""
    space_id = ""
    homepage_id = ""

    try:
        me = get_json("/wiki/rest/api/user/current?expand=personalSpace", auth_b64)
        personal_space = me.get("personalSpace") or {}
        space_key = str(personal_space.get("key") or "")
        space_id = str(personal_space.get("id") or "")
        homepage = personal_space.get("homepage") or {}
        homepage_id = str(homepage.get("id") or "")
    except Exception:
        debug("Confluence current user endpoint did not return a resolvable personalSpace")

    if not space_key or not space_id or not homepage_id:
        derived_space_key = "~" + re.sub(r"[^A-Za-z0-9]", "", account_id)
        debug(f"Falling back to derived personal space key: {derived_space_key}")
        spaces = get_json(
            f"/wiki/api/v2/spaces?keys={urllib.parse.quote(derived_space_key, safe='')}&limit=1",
            auth_b64,
        )
        results = spaces.get("results") or []
        if not results:
            raise RuntimeError("Current Confluence user has no resolvable personal space/homepage")
        space = results[0]
        space_key = str(space.get("key") or derived_space_key)
        space_id = str(space.get("id") or "")
        homepage_id = str(space.get("homepageId") or "")
        if not homepage_id and space_key:
            legacy_space = get_json(
                f"/wiki/rest/api/space/{urllib.parse.quote(space_key, safe='')}?expand=homepage",
                auth_b64,
            )
            homepage_id = str(((legacy_space.get("homepage") or {}).get("id")) or "")
        if not space_id or not homepage_id:
            raise RuntimeError("Current Confluence user has no resolvable personal space/homepage")

    children = get_json(f"/wiki/api/v2/pages/{homepage_id}/direct-children?limit=250", auth_b64)
    results = children.get("results") or []
    workspace_folder = None
    for item in results:
        if str(item.get("title") or "").strip() == "Workspace" and str(item.get("type") or "").strip().lower() == "folder":
            workspace_folder = item
            break

    if workspace_folder is None:
        log("Creating Confluence Workspace folder under My Space")
        workspace_folder = post_json(
            "/wiki/api/v2/folders",
            auth_b64,
            {"title": "Workspace", "spaceId": space_id, "parentId": homepage_id},
        )

    folder_id = str(workspace_folder.get("id") or "")
    if not folder_id:
        raise RuntimeError("Workspace folder creation succeeded but no folder id returned")
    return {
        "workspace_url": f"{ATLASSIAN_BASE_URL.rstrip('/')}/wiki/spaces/{space_key}/folder/{folder_id}",
        "space_key": space_key,
        "parent_id": folder_id,
        "space_id": space_id,
    }


def resolve_project(project_input: str, auth_b64: str) -> dict[str, Any]:
    log(f"Resolving Jira project metadata for {project_input}")
    quoted = urllib.parse.quote(project_input, safe="")
    try:
        project = get_json(f"/rest/api/3/project/{quoted}", auth_b64)
        if project:
            return project
    except Exception:
        pass

    data = get_json(f"/rest/api/3/project/search?query={quoted}&maxResults=50", auth_b64)
    values = data.get("values") or []
    needle = project_input.strip().lower()
    exact = [
        item
        for item in values
        if str(item.get("key") or "").lower() == needle or str(item.get("name") or "").lower() == needle
    ]
    matches = exact or values
    if len(matches) != 1:
        raise RuntimeError(f"Cannot uniquely resolve project from input: {project_input}")
    return matches[0]


def fetch_createmeta(project_key: str, auth_b64: str) -> dict[str, Any]:
    log(f"Fetching Jira create metadata for {project_key}")
    itypes_data = get_json(f"/rest/api/3/issue/createmeta/{project_key}/issuetypes", auth_b64)
    if isinstance(itypes_data, dict) and "issueTypes" in itypes_data:
        itypes = itypes_data["issueTypes"]
    elif isinstance(itypes_data, dict) and "values" in itypes_data:
        itypes = itypes_data["values"]
    elif isinstance(itypes_data, list):
        itypes = itypes_data
    else:
        raise RuntimeError(f"Unexpected createmeta issue types response: {itypes_data!r}")

    items: list[dict[str, Any]] = []
    for issue_type in itypes:
        issue_type_id = issue_type.get("id")
        if not issue_type_id:
            continue
        fields_data = get_json(f"/rest/api/3/issue/createmeta/{project_key}/issuetypes/{issue_type_id}", auth_b64)
        if isinstance(fields_data, dict) and "values" in fields_data:
            fields_page = fields_data["values"]
        elif isinstance(fields_data, dict) and "fields" in fields_data:
            fields_page = fields_data.get("fields", [])
        elif isinstance(fields_data, list):
            fields_page = fields_data
        else:
            fields_page = []

        def field_obj(field: dict[str, Any]) -> dict[str, Any]:
            options = [
                str(o.get("value") or o.get("name") or o.get("id") or "")
                for o in (field.get("allowedValues") or [])
            ]
            return {
                "name": field.get("name", ""),
                "key": field.get("key") or field.get("fieldId") or "",
                "type": (field.get("schema") or {}).get("type", ""),
                "options": [opt for opt in options if opt],
            }

        items.append(
            {
                "issue_type_id": str(issue_type_id),
                "issue_type": issue_type.get("name", ""),
                "required_fields": [field_obj(f) for f in fields_page if f.get("required")],
                "optional_fields": [field_obj(f) for f in fields_page if not f.get("required")],
            }
        )

    return {
        "ok": True,
        "project": project_key,
        "issue_types": [it.get("name") for it in itypes],
        "items": items,
    }


def preferred_default(name: str, options: list[str]) -> str:
    preferred = {
        "Priority": ["Medium", "High", "Highest", "Low"],
        "Story Type": ["Improvement", "New Feature", "API Integration & Enablement"],
        "UX Review Required?": ["No", "Yes"],
        "UX Review Status": ["Not Needed", "Pending", "Reviewed"],
        "Technical Story Type": ["Code Quality", "Architecture", "Others"],
    }
    for candidate in preferred.get(name, []):
        if candidate in options:
            return candidate
    return ""


def build_discovery(
    project: dict[str, Any],
    components_data: list[dict[str, Any]],
    createmeta: dict[str, Any],
    epics_data: dict[str, Any],
    project_key: str,
    account_id: str,
    username: str,
    default_assignee: dict[str, str],
) -> dict[str, Any]:
    project_name = project.get("name") or project_key
    components = sorted(
        [{"name": item.get("name", "").strip()} for item in (components_data or []) if item.get("name", "").strip()],
        key=lambda x: x["name"].lower(),
    )

    issue_types: dict[str, Any] = {}
    supported_work_types: list[str] = []
    for item in createmeta.get("items", []):
        issue_type = item.get("issue_type", "")
        supported_work_types.append(issue_type)
        required_fields: list[str] = []
        optional_fields: list[str] = []
        field_options: dict[str, list[str]] = {}
        field_defaults: dict[str, str] = {}
        key_aliases: dict[str, str] = {}

        for bucket_name, target in (("required_fields", required_fields), ("optional_fields", optional_fields)):
            for field in item.get(bucket_name, []):
                field_name = field.get("name", "").strip()
                if field_name:
                    target.append(field_name)
                options = [str(opt) for opt in field.get("options", []) if str(opt)]
                if options:
                    field_options[field_name] = options
                default_value = preferred_default(field_name, options)
                if field_name == "Client ID":
                    default_value = "0000"
                if default_value:
                    field_defaults[field_name] = default_value
                key_aliases[field_name] = field.get("key", "")

        issue_types[issue_type] = {
            "required_fields": required_fields,
            "optional_fields": optional_fields,
            "field_options": field_options,
            "field_defaults": field_defaults,
            "_field_keys": key_aliases,
        }

    defaults: dict[str, Any] = {
        "client_id": "0000",
        "assignee": {
            "name": default_assignee["name"],
            "account_id": default_assignee["account_id"],
            "role": "",
        },
    }
    if "Epic" in supported_work_types:
        defaults["assignee_by_work_type"] = {
            "Epic": {
                "name": default_assignee["name"],
                "account_id": default_assignee["account_id"],
                "role": "",
            }
        }

    field_alias_rules = {
        "Story": {
            "Client ID": "client_id",
            "Story Type": "story_type",
            "UX Review Required?": "ux_review_required",
            "UX Review Status": "ux_review_status",
        },
        "Technical Story": {
            "Client ID": "client_id",
            "Technical Story Type": "technical_story_type",
        },
    }
    field_mapping_project: dict[str, Any] = {}
    for issue_type, aliases in field_alias_rules.items():
        if issue_type not in issue_types:
            continue
        fields = {}
        for field_name, alias in aliases.items():
            key = issue_types[issue_type]["_field_keys"].get(field_name, "")
            if key:
                fields[alias] = key
        if fields:
            field_mapping_project[issue_type] = {"fields": fields}

    recent_epics = [
        {
            "key": issue.get("key", ""),
            "title": ((issue.get("fields") or {}).get("summary") or "").strip(),
            "components": [
                (component.get("name") or "").strip()
                for component in (((issue.get("fields") or {}).get("components")) or [])
                if (component.get("name") or "").strip()
            ],
        }
        for issue in (epics_data.get("issues") or [])
        if issue.get("key") and ((issue.get("fields") or {}).get("summary") or "").strip()
    ]

    return {
        "project_key": project_key,
        "project_name": project_name,
        "projects_responsible": [project_key],
        "default_project": project_key,
        "components": components,
        "ticket_schema": {
            "schema_version": 1,
            "supported_work_types": supported_work_types,
            "defaults": defaults,
            "issue_types": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in issue_types.items()},
        },
        "field_mapping_project": field_mapping_project,
        "recent_epics": recent_epics,
    }


def render_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(ch in text for ch in [":", "#", "[", "]", "{", "}", '"', "'"]) or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text


def dump_yaml(obj: Any, indent: int = 0) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(dump_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {render_scalar(value)}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                if not item:
                    lines.append(f"{prefix}- {{}}")
                    continue
                first = True
                for key, value in item.items():
                    item_prefix = f"{prefix}- " if first else f"{prefix}  "
                    if isinstance(value, (dict, list)):
                        lines.append(f"{item_prefix}{key}:")
                        lines.extend(dump_yaml(value, indent + 4))
                    else:
                        lines.append(f"{item_prefix}{key}: {render_scalar(value)}")
                    first = False
            else:
                lines.append(f"{prefix}- {render_scalar(item)}")
    return lines


def parse_simple_yaml_map(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        match = re.match(r"^(\s*)([^:\n]+):(?:\s*(.*))?$", line)
        if not match:
            continue
        indent = len(match.group(1))
        key = match.group(2).strip()
        raw_value = (match.group(3) or "").strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if raw_value == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        elif raw_value == "{}":
            parent[key] = {}
        else:
            value = raw_value
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            parent[key] = value
    return root


def parse_recent_epics(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    epics: list[dict[str, Any]] = []
    in_recent = False
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
            current["components"] = [c.strip().strip('"').strip("'") for c in raw.split(",") if c.strip()] if raw else []
    if current:
        epics.append(current)
    return epics


def upsert_env(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replaced = False
    out: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def write_outputs(
    discovery: dict[str, Any],
    username: str,
    display_name: str,
    email: str,
    account_id: str,
    workspace: dict[str, str],
    token: str,
    default_assignee: dict[str, str],
) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.touch(exist_ok=True)

    project_key = discovery["project_key"]
    project_name = discovery["project_name"]
    project_dir = REPO_ROOT / "config" / "assets" / "project" / project_key
    policy_dir = REPO_ROOT / "config" / "policy" / project_key
    project_dir.mkdir(parents=True, exist_ok=True)
    policy_dir.mkdir(parents=True, exist_ok=True)

    profile = {
        "me": {
            "name": username,
            "display_name": display_name or username,
            "email": email,
            "account_id": account_id,
            "projects_responsible": discovery["projects_responsible"],
            "default_project": project_key,
            "confluence_workspace": workspace["workspace_url"],
            "confluence_base_url": ATLASSIAN_BASE_URL,
            "confluence_space_key": workspace["space_key"],
            "confluence_parent_id": workspace["parent_id"],
            "confluence_space_id": workspace["space_id"],
        }
    }
    PROFILE_PATH.write_text("\n".join(dump_yaml(profile)) + "\n", encoding="utf-8")

    components_yaml = {"components": discovery["components"]}
    (project_dir / "components.yaml").write_text("\n".join(dump_yaml(components_yaml)) + "\n", encoding="utf-8")

    team_yaml = {
        "workspace": {
            "name": f"{project_name} Workspace",
            "project": {"key": project_key},
            "ownership": {"components_file": "components.yaml"},
        },
        "team": {
            "default_assignee": {
                "name": default_assignee["name"],
                "email": default_assignee["email"],
                "account_id": default_assignee["account_id"],
            },
            "members": [],
            "external_members": [],
        },
    }
    (project_dir / "team.yaml").write_text("\n".join(dump_yaml(team_yaml)) + "\n", encoding="utf-8")

    (policy_dir / "ticket-schema.json").write_text(
        json.dumps(discovery["ticket_schema"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    field_mappings_path = policy_dir.parent / "field-mappings.yaml"
    existing = {"defaults": {}, "projects": {}}
    if field_mappings_path.is_file():
        existing = parse_simple_yaml_map(field_mappings_path.read_text(encoding="utf-8"))
    defaults = existing.get("defaults") or {}
    projects = existing.get("projects") or {}
    projects[project_key] = discovery["field_mapping_project"]
    field_mappings_path.write_text(
        "\n".join(dump_yaml({"defaults": defaults, "projects": projects})) + "\n",
        encoding="utf-8",
    )

    epic_list_path = PROFILE_PATH.parent / "epic-list.yaml"
    existing_recent_epics: list[dict[str, Any]] = []
    if epic_list_path.is_file():
        existing_recent_epics = parse_recent_epics(epic_list_path.read_text(encoding="utf-8"))
    project_prefix = f"{project_key.upper()}-"
    merged_recent_epics = [
        item for item in existing_recent_epics if not str(item.get("key", "")).startswith(project_prefix)
    ]
    merged_recent_epics.extend(discovery.get("recent_epics") or [])
    epic_list_lines = [
        "# Global epic list: conventions and recent epics. Project implied by key prefix (CP-, PAG-).",
        "",
        "epic_management:",
        "  purpose: Manage Story parent linkage through quarterly module epics.",
        "  conventions:",
        '    quarterly_module_epic_naming_pattern: "<Module> Upgrade - <YYQn>"',
        '    story_parent_default_rule: "For functional-module Story, default Parent to module quarterly Epic."',
        '    special_epic_override_rule: "Use a special Epic when user explicitly specifies one or the work is non-quarterly."',
        "",
        "  # JQL template to fetch recent epics (project scope, not Done/Won't Do, last 24w).",
        "  recent_epics_query:",
        '    description: "My project epics, open, created in last 24 weeks"',
        "    jql_template: |",
        "      type = Epic",
        "      AND project = {{project_key}}",
        "      AND reporter = {{reporter_account_id}}",
        '      AND status NOT IN (Done, "Won\'t Do")',
        "      AND created >= -24w",
        "      ORDER BY created DESC",
        "    # MCP tool to run this query and refresh recent_epics:",
        "    mcp:",
        "      server: user-mcp-atlassian",
        "      tool: jira_search",
        "      params:",
        '        jql: "jql_template with {{project_key}} and {{reporter_account_id}} replaced"',
        '        fields: "key,summary,components"',
        "        limit: 50",
        "",
        "  recent_epics:",
    ]
    if merged_recent_epics:
        epic_list_lines.extend(dump_yaml(merged_recent_epics, 4))
    epic_list_path.write_text("\n".join(epic_list_lines) + "\n", encoding="utf-8")

    upsert_env(ENV_PATH, "CONFLUENCE_EMAIL", email)
    upsert_env(ENV_PATH, "ATLASSIAN_API_TOKEN", token)
    upsert_env(ENV_PATH, "ACCOUNT_ID", account_id)
    upsert_env(ENV_PATH, "CONFLUENCE_BASE_URL", ATLASSIAN_BASE_URL)
    upsert_env(ENV_PATH, "CONFLUENCE_SPACE_KEY", workspace["space_key"])
    upsert_env(ENV_PATH, "CONFLUENCE_PARENT_ID", workspace["parent_id"])
    upsert_env(ENV_PATH, "CONFLUENCE_SPACE_ID", workspace["space_id"])

    log("Initialization completed.")
    print(f"Generated: {PROFILE_PATH}")
    print("  Purpose: personal identity, default project, and Confluence workspace settings.")
    print(f"Updated:   {ENV_PATH}")
    print("  Purpose: local secrets and runtime environment values for Jira/Confluence scripts.")
    print(f"Generated: {project_dir / 'components.yaml'}")
    print("  Purpose: project component catalog fetched from Jira.")
    print(f"Generated: {project_dir / 'team.yaml'}")
    print("  Purpose: project team skeleton. members/external_members are intentionally left empty.")
    print(f"Generated: {policy_dir / 'ticket-schema.json'}")
    print("  Purpose: executable Jira issue schema, defaults, and allowed field options.")
    print(f"Updated:   {field_mappings_path}")
    print("  Purpose: alias-to-Jira custom field mapping used by creation scripts.")
    print(f"Updated:   {epic_list_path}")
    print("  Purpose: recent Epic cache used for Story parent auto-selection.")


def prompt_default_assignee(project_key: str, auth_b64: str) -> dict[str, str]:
    while True:
        assignee_input = prompt_non_empty("Input default assignee email: ")
        target = assignee_input.strip().lower()
        quoted_target = urllib.parse.quote(assignee_input.strip(), safe="")
        users = get_json(
            f"/rest/api/3/user/assignable/search?project={project_key}&query={quoted_target}&maxResults=20",
            auth_b64,
        )
        match = None
        for user in users or []:
            email = str(user.get("emailAddress") or "").strip()
            if email.lower() == target:
                match = {
                    "name": str(user.get("displayName") or email or user.get("accountId") or "").strip(),
                    "email": email,
                    "account_id": str(user.get("accountId") or "").strip(),
                }
                break
        if not match:
            fail(f"Default assignee not found in project {project_key}. Please retry.")
            continue
        print(
            "Default assignee found: "
            f"{match['name']} <{match['email']}> ({match['account_id']})"
        )
        confirm = input("Use this assignee? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            return match


def prompt_validated_credentials() -> tuple[str, str, dict[str, str]]:
    while True:
        print("Step 1/3 - Email")
        email = prompt_email()
        print("Step 2/3 - Project Name or Key")
        project_input = prompt_non_empty('Input project name or key (e.g. "CP" or "Common Platform"): ')
        print("Step 3/3 - ATLASSIAN_API_TOKEN")
        token = prompt_non_empty("Input ATLASSIAN_API_TOKEN: ", secret=True)
        try:
            identity = validate_identity(email, token)
            return email, project_input, {"token": token, **identity}
        except (HTTPError, URLError, RuntimeError) as exc:
            fail(f"Email or token validation failed: {exc}")
            print("Please retry your email and token.\n")


def main() -> int:
    try:
        email, project_input, creds = prompt_validated_credentials()
        token = creds["token"]
        auth_b64 = creds["auth_b64"]
        account_id = creds["account_id"]
        display_name = creds["display_name"]
        username = derive_username(email, display_name)

        workspace = resolve_default_workspace(auth_b64, account_id)
        project = resolve_project(project_input, auth_b64)
        project_key = str(project.get("key") or "").upper()
        if not project_key:
            raise RuntimeError("resolved project key is empty")

        log(f"Fetching Jira components for {project_key}")
        components_data = get_json(f"/rest/api/3/project/{project_key}/components", auth_b64)

        default_assignee = prompt_default_assignee(project_key, auth_b64)

        log(f"Fetching recent epics for {project_key}")
        epics_data = post_json(
            "/rest/api/3/search/jql",
            auth_b64,
            {
                "jql": (
                    f"project = {project_key} "
                    'AND issuetype = Epic '
                    f'AND reporter = "{account_id}" '
                    'AND status NOT IN (Done, "Won\'t Do") '
                    "AND created >= -24w "
                    "ORDER BY created DESC"
                ),
                "maxResults": 50,
                "fields": ["key", "summary", "components"],
            },
        )

        createmeta = fetch_createmeta(project_key, auth_b64)
        log("Building project discovery payload")
        discovery = build_discovery(
            project,
            components_data,
            createmeta,
            epics_data,
            project_key,
            account_id,
            username,
            default_assignee,
        )
        log("Writing profile, team, components, schema, field mapping, and epic list")
        write_outputs(
            discovery,
            username,
            display_name,
            email,
            account_id,
            workspace,
            token,
            default_assignee,
        )
        return 0
    except KeyboardInterrupt:
        fail("Initialization cancelled.")
        return 130
    except Exception as exc:
        fail(str(exc))
        if debug_enabled():
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
