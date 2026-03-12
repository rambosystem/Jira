#!/usr/bin/env python3
"""
Delete from a Jira issue the remote link that points to a specific Confluence page.
Used to remove the "mentioned in" link from PIN to the published Wiki page (only that link).

Jira API: GET /rest/api/3/issue/{key}/remotelink, then
          DELETE /rest/api/3/issue/{key}/remotelink?globalId={urlencoded(globalId)}

Usage:
  python scripts/jira/delete_issue_remotelink.py --issue PIN-2805 --confluence-page-id 1261699359
  python scripts/jira/delete_issue_remotelink.py -i PIN-2805 -p 1261699359
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth
from scripts.common.env import load_dotenv
from scripts.common.jira_remotelinks import delete_remotelink_for_confluence_page
from scripts.common.profile import load_atlassian_profile

PROFILE_PATH = REPO_ROOT / "Assets" / "Global" / "profile.yaml"
ENV_PATH = REPO_ROOT / ".env"


def main() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(
        description="Delete the remote link from a Jira issue to a Confluence page (only that link)."
    )
    parser.add_argument("--issue", "-i", required=True, help="Jira issue key, e.g. PIN-2805")
    parser.add_argument(
        "--confluence-page-id",
        "-p",
        required=True,
        help="Confluence page ID (number) that the link points to, e.g. 1261699359",
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
    try:
        deleted = delete_remotelink_for_confluence_page(
            base_url, auth, args.issue, args.confluence_page_id
        )
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error {e.code}: {body}", file=sys.stderr)
        return 1
    if deleted:
        print(f"Deleted remotelink for {args.issue} → Confluence page {args.confluence_page_id}")
    else:
        print(f"No Confluence remotelink found for {args.issue} pointing to page {args.confluence_page_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
