#!/usr/bin/env python3
"""GET /rest/api/3/issue/{issueIdOrKey}/remotelink - list remote links (e.g. Wiki) for a Jira issue."""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

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


def main():
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Get remote links for a Jira issue")
    parser.add_argument("issue", nargs="?", default="PIN-2805", help="Issue key, e.g. PIN-2805")
    parser.add_argument(
        "--output-file",
        default="",
        help="Optional: write full remotelinks JSON to file.",
    )
    args = parser.parse_args()

    try:
        profile = load_atlassian_profile(PROFILE_PATH)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    base_url = profile["base_url"]
    email = profile["email"]
    token = os.environ.get("ATLASSIAN_API_TOKEN", "")
    if not base_url:
        print("Error: confluence_base_url not in profile.", file=sys.stderr)
        return 1
    if not email or not token:
        print("Error: need email (profile or CONFLUENCE_EMAIL) and ATLASSIAN_API_TOKEN.", file=sys.stderr)
        return 1

    auth = basic_auth(email, token)
    url = jira_api_v3_url(base_url, f"/issue/{args.issue}/remotelink")
    try:
        data = request_json(
            url,
            headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
            insecure_env_var="JIRA_INSECURE_SSL",
        )
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error {e.code}: {body}", file=sys.stderr)
        return 1
    except URLError as e:
        print(f"Error: network request failed: {e}", file=sys.stderr)
        return 1
    output_path = None
    if args.output_file:
        output_path = Path(args.output_file)
        if not output_path.is_absolute():
            output_path = REPO_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    count = len(data) if isinstance(data, list) else len((data or {}).get("values", []))
    if output_path:
        print(f"DONE get_issue_remotelinks issue={args.issue} count={count} output={output_path}")
    else:
        print(f"DONE get_issue_remotelinks issue={args.issue} count={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
