#!/usr/bin/env python3
"""
Fetch Jira create metadata for a project: issue types, required/optional fields, and field options.

Usage:
  get_createmeta.py [project_key]              # fields only
  get_createmeta.py [project_key] --options     # include allowedValues for option-type fields

Calls:
  GET /rest/api/3/issue/createmeta/{projectKey}/issuetypes
  GET /rest/api/3/issue/createmeta/{projectKey}/issuetypes/{issueTypeId}
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth, jira_api_v3_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.profile import load_atlassian_profile, resolve_profile_path

PROFILE_PATH = resolve_profile_path(REPO_ROOT)
ENV_PATH = REPO_ROOT / ".env"


def _get(base_url: str, auth: str, path: str) -> dict | list:
    url = jira_api_v3_url(base_url, path)
    return request_json(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {auth}",
        },
    )


def main() -> None:
    load_dotenv(ENV_PATH)
    profile = load_atlassian_profile(PROFILE_PATH)
    base_url = profile["base_url"]
    email = profile["email"]
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("Error: ATLASSIAN_API_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)
    auth = basic_auth(email, token)
    args = [a for a in sys.argv[1:] if a.strip()]
    with_options = "--options" in args or "-o" in args
    project_key = next((a for a in args if not a.startswith("-")), "PACID").strip()

    # 1) List issue types for project
    path_itypes = f"/issue/createmeta/{project_key}/issuetypes"
    itypes_data = _get(base_url, auth, path_itypes)
    if isinstance(itypes_data, dict) and "issueTypes" in itypes_data:
        itypes = itypes_data["issueTypes"]
    elif isinstance(itypes_data, dict) and "values" in itypes_data:
        itypes = itypes_data["values"]
    elif isinstance(itypes_data, list):
        itypes = itypes_data
    else:
        print("Unexpected issue types response:", json.dumps(itypes_data, indent=2)[:500], file=sys.stderr)
        sys.exit(1)

    if not itypes:
        print(f"No issue types for project {project_key}.", file=sys.stderr)
        sys.exit(0)

    print(f"Project: {project_key}")
    print(f"Issue types: {[t.get('name') for t in itypes]}\n")

    for it in itypes:
        it_id = it.get("id")
        it_name = it.get("name", "?")
        if it_id is None:
            continue
        path_fields = f"/issue/createmeta/{project_key}/issuetypes/{it_id}"
        fields_data = _get(base_url, auth, path_fields)
        if isinstance(fields_data, dict) and "values" in fields_data:
            fields_page = fields_data["values"]
        elif isinstance(fields_data, dict) and "fields" in fields_data:
            fields_page = fields_data.get("fields", [])
        elif isinstance(fields_data, list):
            fields_page = fields_data
        else:
            fields_page = []

        required = [f for f in fields_page if f.get("required")]
        optional = [f for f in fields_page if not f.get("required")]

        def _fmt_field(f: dict, show_options: bool) -> str:
            key = f.get("key") or f.get("fieldId") or "?"
            name = f.get("name", key)
            schema = f.get("schema", {})
            schema_type = schema.get("type", "")
            line = f"  - {name} (key={key}, type={schema_type})"
            if show_options and f.get("allowedValues"):
                vals = [str(o.get("value") or o.get("name") or o.get("id", "")) for o in f["allowedValues"]]
                line += f"\n      options: {vals}"
            return line

        print(f"--- {it_name} (id={it_id}) ---")
        print("Required fields:")
        for f in required:
            print(_fmt_field(f, with_options))
        print("Optional fields:")
        for f in optional:
            print(_fmt_field(f, with_options))
        print()

    # Optional: dump raw JSON for one issue type (e.g. Idea)
    if "--json" in args:
        it_name_arg = next((args[i + 1] for i, a in enumerate(args) if a == "--json" and i + 1 < len(args) and not args[i + 1].startswith("-")), "Idea")
        for it in itypes:
            if it.get("name") == it_name_arg:
                path_fields = f"/issue/createmeta/{project_key}/issuetypes/{it.get('id')}"
                print(json.dumps(_get(base_url, auth, path_fields), indent=2))
                break


if __name__ == "__main__":
    main()
