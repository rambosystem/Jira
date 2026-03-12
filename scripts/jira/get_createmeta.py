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

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError

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


def main() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Fetch Jira createmeta and write result to JSON file.")
    parser.add_argument("project_key", nargs="?", default="PACID")
    parser.add_argument("--options", "-o", action="store_true", help="Include allowedValues for option fields.")
    parser.add_argument(
        "--json",
        dest="json_issue_type",
        default="",
        help="Also include raw createmeta for specified issue type name.",
    )
    parser.add_argument(
        "--output-file",
        default="",
        help="Optional: write full result JSON to file.",
    )
    args = parser.parse_args()

    profile = load_atlassian_profile(PROFILE_PATH)
    base_url = profile["base_url"]
    email = profile["email"]
    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("Error: ATLASSIAN_API_TOKEN not set in .env", file=sys.stderr)
        return 1
    auth = basic_auth(email, token)
    with_options = args.options
    project_key = args.project_key.strip()

    path_itypes = f"/issue/createmeta/{project_key}/issuetypes"
    try:
        itypes_data = _get(base_url, auth, path_itypes)
    except URLError as exc:
        print(f"Error: network request failed: {exc}", file=sys.stderr)
        return 1
    if isinstance(itypes_data, dict) and "issueTypes" in itypes_data:
        itypes = itypes_data["issueTypes"]
    elif isinstance(itypes_data, dict) and "values" in itypes_data:
        itypes = itypes_data["values"]
    elif isinstance(itypes_data, list):
        itypes = itypes_data
    else:
        print(
            "Error: unexpected issue types response: "
            + json.dumps(itypes_data, ensure_ascii=False)[:300],
            file=sys.stderr,
        )
        return 1

    if not itypes:
        result = {"ok": True, "project": project_key, "issue_types": [], "items": []}
        if args.output_file:
            out = Path(args.output_file)
            if not out.is_absolute():
                out = REPO_ROOT / out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"DONE get_createmeta project={project_key} issue_types=0 output={out}")
        else:
            print(f"DONE get_createmeta project={project_key} issue_types=0")
        return 0

    items: list[dict] = []

    for it in itypes:
        it_id = it.get("id")
        it_name = it.get("name", "?")
        if it_id is None:
            continue
        path_fields = f"/issue/createmeta/{project_key}/issuetypes/{it_id}"
        try:
            fields_data = _get(base_url, auth, path_fields)
        except URLError as exc:
            print(f"Error: network request failed: {exc}", file=sys.stderr)
            return 1
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

        def _field_obj(f: dict, show_options: bool) -> dict:
            key = f.get("key") or f.get("fieldId") or "?"
            name = f.get("name", key)
            schema = f.get("schema", {})
            schema_type = schema.get("type", "")
            obj = {"name": name, "key": key, "type": schema_type}
            if show_options and f.get("allowedValues"):
                obj["options"] = [str(o.get("value") or o.get("name") or o.get("id", "")) for o in f["allowedValues"]]
            return obj

        items.append(
            {
                "issue_type_id": str(it_id),
                "issue_type": it_name,
                "required_fields": [_field_obj(f, with_options) for f in required],
                "optional_fields": [_field_obj(f, with_options) for f in optional],
            }
        )

    raw_issue_type_data = None
    if args.json_issue_type:
        it_name_arg = args.json_issue_type
        for it in itypes:
            if it.get("name") == it_name_arg:
                path_fields = f"/issue/createmeta/{project_key}/issuetypes/{it.get('id')}"
                try:
                    raw_issue_type_data = _get(base_url, auth, path_fields)
                except URLError as exc:
                    print(f"Error: network request failed: {exc}", file=sys.stderr)
                    return 1
                break

    result = {
        "ok": True,
        "project": project_key,
        "issue_types": [t.get("name") for t in itypes],
        "items": items,
    }
    if raw_issue_type_data is not None:
        result["raw_issue_type_data"] = raw_issue_type_data

    if args.output_file:
        out = Path(args.output_file)
        if not out.is_absolute():
            out = REPO_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DONE get_createmeta project={project_key} issue_types={len(itypes)} output={out}")
    else:
        print(f"DONE get_createmeta project={project_key} issue_types={len(itypes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
