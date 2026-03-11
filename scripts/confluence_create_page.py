#!/usr/bin/env python3
"""
Create or update a Confluence page with ADF body via REST API v2.
Reads confluence_* from Assets/Global/profile.yaml. Auth: CONFLUENCE_EMAIL + ATLASSIAN_API_TOKEN.

Flow: Look up page by title → if exists, append (merge ADF) and PUT; else POST new page.
Body from: --body-stdin, --body-file (relative path → repo tmp/), --body-json, --jira-url.
Temp files live under repo tmp/; we only overwrite, never delete.

Usage:
  set ATLASSIAN_API_TOKEN=your_token
  python scripts/confluence_create_page.py --title "My Page" --body-file pin_report_adf.json
  python scripts/confluence_create_page.py -t "My Page" --jira-url "https://.../browse/PIN-123"
"""

import argparse
import base64
import json
import os
import re
import ssl
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import quote


def _ssl_context() -> ssl.SSLContext:
    """Use certifi CA bundle so HTTPS works on macOS (Python.org installs often miss system certs)."""
    if os.environ.get("CONFLUENCE_INSECURE_SSL") == "1":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return ctx


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TMP_DIR = REPO_ROOT / "tmp"
PROFILE_PATH = REPO_ROOT / "Assets" / "Global" / "profile.yaml"
ENV_PATH = REPO_ROOT / ".env"


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
    if "EMAIL" in os.environ and "CONFLUENCE_EMAIL" not in os.environ:
        os.environ.setdefault("CONFLUENCE_EMAIL", os.environ["EMAIL"])


def load_profile() -> dict:
    if not PROFILE_PATH.is_file():
        print(f"Error: Profile not found: {PROFILE_PATH}", file=sys.stderr)
        sys.exit(1)
    text = PROFILE_PATH.read_text(encoding="utf-8")

    def get(key: str) -> Optional[str]:
        m = re.search(rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'#\n]+)[\"']?\s*(?:#|$)", text, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
        m = re.search(rf"^\s*{re.escape(key)}\s*:\s*\"([^\"]+)\"", text, re.MULTILINE)
        return m.group(1) if m else None

    base_url = get("confluence_base_url")
    space_id = get("confluence_space_id")
    parent_id = get("confluence_parent_id")
    email = get("email") or os.environ.get("CONFLUENCE_EMAIL", "")
    if not all([base_url, space_id, parent_id]):
        print("Error: Profile must set confluence_base_url, confluence_space_id, confluence_parent_id.", file=sys.stderr)
        sys.exit(1)
    return {
        "confluence_base_url": base_url.rstrip("/"),
        "confluence_space_id": space_id,
        "confluence_parent_id": parent_id,
        "email": email or os.environ.get("CONFLUENCE_EMAIL", ""),
    }


def api_request(
    base_url: str,
    auth: str,
    method: str,
    path: str,
    data: Optional[dict] = None,
) -> dict:
    url = f"{base_url}/wiki/api/v2{path}"
    headers = {"Accept": "application/json", "Authorization": f"Basic {auth}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=json.dumps(data).encode("utf-8") if data else None, method=method, headers=headers)
    with urlopen(req, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode())


def find_page_by_title(base_url: str, auth: str, space_id: str, title: str) -> Optional[dict]:
    path = f"/pages?space-id={space_id}&title={quote(title)}&limit=1"
    try:
        data = api_request(base_url, auth, "GET", path)
        results = data.get("results") or []
        return results[0] if results else None
    except HTTPError:
        return None


def get_page_body(base_url: str, auth: str, page_id: str) -> tuple[Optional[dict], int]:
    """Returns (adf_doc, version_number)."""
    try:
        data = api_request(base_url, auth, "GET", f"/pages/{page_id}?body-format=atlas_doc_format")
        body = data.get("body") or {}
        raw = body.get("atlas_doc_format", {}).get("value") or body.get("value")
        version = (data.get("version") or {}).get("number", 1)
        if not raw:
            return None, version
        adf = json.loads(raw) if isinstance(raw, str) else raw
        return adf, version
    except (HTTPError, json.JSONDecodeError):
        return None, 1


def merge_adf_content(existing: Optional[dict], new_content: list) -> dict:
    base = existing if existing and existing.get("type") == "doc" else {"version": 1, "type": "doc", "content": []}
    prev = base.get("content") or []
    merged = prev + [{"type": "rule"}] + new_content
    return {**base, "content": merged}


def build_adf_from_args(args: argparse.Namespace, tmp_dir: Path) -> str:
    """Returns ADF JSON string. Body file: relative path → tmp_dir."""
    if args.body_stdin:
        return sys.stdin.read()
    if args.body_file:
        path = Path(args.body_file)
        if not path.is_absolute():
            path = tmp_dir / path
        return path.read_text(encoding="utf-8")
    if args.body_json:
        return args.body_json
    if args.jira_url:
        doc = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "blockCard", "attrs": {"url": args.jira_url}}],
        }
        return json.dumps(doc, ensure_ascii=False)
    doc = {
        "version": 1,
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.title}]}],
    }
    return json.dumps(doc, ensure_ascii=False)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Create or append Confluence page (ADF) via REST API v2")
    parser.add_argument("--title", "-t", required=True, help="Page title")
    parser.add_argument("--jira-url", "-j", default="", help="Jira issue URL for blockCard (optional)")
    parser.add_argument("--body-json", "-b", default="", help="Full ADF JSON string")
    parser.add_argument("--body-file", default="", help="Path to ADF JSON file (relative → repo tmp/)")
    parser.add_argument("--body-stdin", action="store_true", help="Read ADF JSON from stdin")
    args = parser.parse_args()

    token = os.environ.get("ATLASSIAN_API_TOKEN")
    if not token:
        print("Error: Set ATLASSIAN_API_TOKEN.", file=sys.stderr)
        sys.exit(1)

    profile = load_profile()
    base_url = profile["confluence_base_url"]
    space_id = profile["confluence_space_id"]
    parent_id = profile["confluence_parent_id"]
    email = profile["email"]
    if not email:
        print("Error: Set CONFLUENCE_EMAIL or me.email in profile.", file=sys.stderr)
        sys.exit(1)

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    new_adf_raw = build_adf_from_args(args, TMP_DIR)
    new_adf = json.loads(new_adf_raw) if isinstance(new_adf_raw, str) else new_adf_raw
    new_content = new_adf.get("content") or []

    existing = find_page_by_title(base_url, auth, space_id, args.title)
    if existing:
        page_id = existing["id"]
        current_adf, version = get_page_body(base_url, auth, page_id)
        merged = merge_adf_content(current_adf, new_content)
        payload = {
            "id": page_id,
            "status": "current",
            "title": args.title,
            "version": {"number": version + 1},
            "body": {"representation": "atlas_doc_format", "value": json.dumps(merged, ensure_ascii=False)},
        }
        try:
            out = api_request(base_url, auth, "PUT", f"/pages/{page_id}", payload)
        except HTTPError as e:
            print(f"Error {e.code}: {e.read().decode() if e.fp else ''}", file=sys.stderr)
            sys.exit(1)
        webui = (out.get("_links") or {}).get("webui", "") or ""
        page_url = (base_url + webui) if webui.startswith("/") else (base_url + "/" + webui) if webui else ""
        print(f"Page updated (appended): id={page_id}")
        print(f"URL: {page_url}")
    else:
        payload = {
            "spaceId": space_id,
            "status": "current",
            "title": args.title,
            "parentId": parent_id,
            "body": {"representation": "atlas_doc_format", "value": new_adf_raw},
        }
        try:
            out = api_request(base_url, auth, "POST", "/pages", payload)
        except HTTPError as e:
            print(f"Error {e.code}: {e.read().decode() if e.fp else ''}", file=sys.stderr)
            sys.exit(1)
        page_id = out.get("id")
        webui = (out.get("_links") or {}).get("webui", "") or ""
        page_url = (base_url + webui) if webui.startswith("/") else (base_url + "/" + webui) if webui else ""
        print(f"Page created: id={page_id}")
        print(f"URL: {page_url}")


if __name__ == "__main__":
    main()
