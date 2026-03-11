#!/usr/bin/env python3
"""
Delete from a Jira issue the remote link that points to a specific Confluence page.
Used to remove the "mentioned in" link from PIN to the published Wiki page (only that link).

Jira API: GET /rest/api/3/issue/{key}/remotelink, then
          DELETE /rest/api/3/issue/{key}/remotelink?globalId={urlencoded(globalId)}

Usage:
  python scripts/delete_issue_remotelink.py --issue PIN-2805 --confluence-page-id 1261699359
  python scripts/delete_issue_remotelink.py -i PIN-2805 -p 1261699359
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PROFILE_PATH = REPO_ROOT / "Assets" / "Global" / "profile.yaml"
ENV_PATH = REPO_ROOT / ".env"


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return ctx


def load_dotenv() -> None:
    if not ENV_PATH.is_file():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("'\"").strip()
        if k:
            os.environ.setdefault(k, v)


def profile_value(text: str, key: str) -> str:
    m = re.search(
        rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'#\n]+)[\"']?\s*(?:#|$)",
        text,
        re.MULTILINE,
    )
    return m.group(1).strip().strip('"').strip("'") if m else ""


def get_remotelinks(base_url: str, auth: str, issue_key: str) -> list[dict]:
    url = f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_key}/remotelink"
    req = Request(url, headers={"Accept": "application/json", "Authorization": f"Basic {auth}"})
    with urlopen(req, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def delete_remotelink_by_link_id(base_url: str, auth: str, issue_key: str, link_id: int) -> None:
    url = f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_key}/remotelink/{link_id}"
    req = Request(
        url,
        method="DELETE",
        headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urlopen(req, context=_ssl_context()) as resp:
        pass


def delete_remotelink_for_confluence_page(
    base_url: str,
    auth: str,
    issue_key: str,
    confluence_page_id: str | int,
) -> bool:
    """
    Delete from the Jira issue the remote link that points to the given Confluence page.
    Returns True if a link was found and deleted, False if no matching link.
    """
    page_id_str = str(confluence_page_id)
    links = get_remotelinks(base_url, auth, issue_key)
    for link in links:
        app = link.get("application") or {}
        if app.get("type") != "com.atlassian.confluence":
            continue
        global_id = link.get("globalId") or ""
        obj = link.get("object") or {}
        obj_url = (obj.get("url") or "") or ""
        if page_id_str in global_id or page_id_str in obj_url:
            link_id = link.get("id")
            if link_id is not None:
                delete_remotelink_by_link_id(base_url, auth, issue_key, int(link_id))
                return True
    return False
    return False


def main() -> int:
    load_dotenv()
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

    if not PROFILE_PATH.is_file():
        print(f"Error: Profile not found: {PROFILE_PATH}", file=sys.stderr)
        return 1
    text = PROFILE_PATH.read_text(encoding="utf-8")
    base_url = profile_value(text, "confluence_base_url")
    email = profile_value(text, "email") or os.environ.get("CONFLUENCE_EMAIL", "")
    token = os.environ.get("ATLASSIAN_API_TOKEN", "")
    if not base_url:
        print("Error: confluence_base_url not in profile.", file=sys.stderr)
        return 1
    if not email or not token:
        print("Error: need email (profile or CONFLUENCE_EMAIL) and ATLASSIAN_API_TOKEN.", file=sys.stderr)
        return 1

    base_url = base_url.rstrip("/")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
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
