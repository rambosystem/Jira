#!/usr/bin/env python3
"""
Create a Confluence page with ADF body via REST API v2.
Reads confluence_base_url, confluence_space_id, confluence_parent_id from Assets/Global/profile.yaml.
Auth: CONFLUENCE_EMAIL + CONFLUENCE_API_TOKEN (env); or me.email from profile + token from env.

Usage:
  export CONFLUENCE_API_TOKEN=your_token
  python scripts/confluence_create_page.py --title "My Page" [--jira-url "https://.../browse/PIN-123"]
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Profile path: repo_root/Assets/Global/profile.yaml
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PROFILE_PATH = REPO_ROOT / "Assets" / "Global" / "profile.yaml"
ENV_PATH = REPO_ROOT / ".env"


def load_dotenv() -> None:
    """Load .env into os.environ (KEY=VALUE, no quotes required)."""
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
    if "EMAIL" in os.environ and "CONFLUENCE_EMAIL" not in os.environ:
        os.environ.setdefault("CONFLUENCE_EMAIL", os.environ["EMAIL"])


def load_profile():
    if not PROFILE_PATH.is_file():
        print(f"Error: Profile not found: {PROFILE_PATH}", file=sys.stderr)
        sys.exit(1)
    text = PROFILE_PATH.read_text(encoding="utf-8")
    # Simple extraction: key: "value" or key: value (no quotes)
    def get(key: str) -> Optional[str]:
        # Match: optional spaces, key, :, optional spaces, optional ", value without ", optional "
        m = re.search(rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'#\n]+)[\"']?\s*(?:#|$)", text, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
        m = re.search(rf"^\s*{re.escape(key)}\s*:\s*\"([^\"]+)\"", text, re.MULTILINE)
        if m:
            return m.group(1)
        return None

    base_url = get("confluence_base_url")
    space_id = get("confluence_space_id")
    parent_id = get("confluence_parent_id")
    email = get("email")  # under me, may be on same level in flat parse
    # If profile has 'me:' block, email might be after 'email:'; our regex finds first match
    if not email:
        email = os.environ.get("CONFLUENCE_EMAIL", "")
    if not base_url or not space_id or not parent_id:
        print("Error: Profile must set confluence_base_url, confluence_space_id, confluence_parent_id.", file=sys.stderr)
        sys.exit(1)
    return {
        "confluence_base_url": base_url,
        "confluence_space_id": space_id,
        "confluence_parent_id": parent_id,
        "email": email or os.environ.get("CONFLUENCE_EMAIL", ""),
    }


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Create Confluence page (ADF) via REST API v2")
    parser.add_argument("--title", "-t", required=True, help="Page title")
    parser.add_argument("--jira-url", "-j", default="", help="Jira issue URL for blockCard (optional)")
    parser.add_argument("--body-json", "-b", default="", help="Full ADF JSON string (overrides --jira-url if set)")
    args = parser.parse_args()

    token = os.environ.get("CONFLUENCE_API_TOKEN")
    if not token:
        print("Error: Set CONFLUENCE_API_TOKEN.", file=sys.stderr)
        sys.exit(1)

    profile = load_profile()
    base_url = profile["confluence_base_url"].rstrip("/")
    space_id = profile["confluence_space_id"]
    parent_id = profile["confluence_parent_id"]
    email = profile["email"] or os.environ.get("CONFLUENCE_EMAIL")
    if not email:
        print("Error: Set CONFLUENCE_EMAIL or set me.email in profile.", file=sys.stderr)
        sys.exit(1)

    # Build ADF body
    if args.body_json:
        adf_value = args.body_json
    elif args.jira_url:
        adf_doc = {
            "version": 1,
            "type": "doc",
            "content": [
                {"type": "blockCard", "attrs": {"url": args.jira_url}},
            ],
        }
        adf_value = json.dumps(adf_doc, ensure_ascii=False)
    else:
        adf_doc = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.title}]}],
        }
        adf_value = json.dumps(adf_doc, ensure_ascii=False)

    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": args.title,
        "parentId": parent_id,
        "body": {
            "representation": "atlas_doc_format",
            "value": adf_value,
        },
    }
    url = f"{base_url}/wiki/api/v2/pages"
    data = json.dumps(payload).encode("utf-8")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = Request(url, data=data, method="POST", headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth}",
    })

    try:
        with urlopen(req) as resp:
            out = json.loads(resp.read().decode())
        page_id = out.get("id")
        webui = (out.get("_links") or {}).get("webui", "") or ""
        page_url = (base_url + webui) if webui.startswith("/") else (base_url + "/" + webui) if webui else ""
        print(f"Page created: id={page_id}")
        print(f"URL: {page_url}")
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
