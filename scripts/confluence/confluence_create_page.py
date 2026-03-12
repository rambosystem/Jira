#!/usr/bin/env python3
"""
Create or update a Confluence page with ADF body via REST API v2.
Reads confluence_* from assets/global/profile.yaml. Auth: CONFLUENCE_EMAIL + ATLASSIAN_API_TOKEN.

Flow: Look up page by title → if exists, append (merge ADF) and PUT; else POST new page.
Body from: --body-stdin, --body-file (relative path → repo tmp/), --body-json, --jira-url.
Temp files live under repo tmp/; we only overwrite, never delete.

By default, PIN issue keys are auto-detected from blockCard URLs in the body and their
remotelink to this Confluence page is removed after publish. Use --no-unlink to skip; use
--unlink-issues to override the list.

Usage:
  set ATLASSIAN_API_TOKEN=your_token
  python scripts/confluence/confluence_create_page.py --title "My Page" --body-file pin_report_adf.json
  python scripts/confluence/confluence_create_page.py -t "My Page" --body-file pin_report_adf.json --no-unlink
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError
from urllib.parse import quote


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth, confluence_api_v2_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.jira_remotelinks import delete_remotelink_for_confluence_page
from scripts.common.profile import load_atlassian_profile, resolve_profile_path

TMP_DIR = REPO_ROOT / "tmp"
PROFILE_PATH = resolve_profile_path(REPO_ROOT)
ENV_PATH = REPO_ROOT / ".env"


def api_request(
    base_url: str,
    auth: str,
    method: str,
    path: str,
    data: Optional[dict] = None,
) -> dict:
    url = confluence_api_v2_url(base_url, path)
    headers = {"Accept": "application/json", "Authorization": f"Basic {auth}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    return request_json(
        url,
        method=method,
        headers=headers,
        data=data,
        insecure_env_var="CONFLUENCE_INSECURE_SSL",
    )


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


def extract_pin_keys_from_adf(adf_doc: dict) -> list[str]:
    """Extract PIN-* issue keys from blockCard URLs in ADF content (e.g. .../browse/PIN-2805)."""
    content = adf_doc.get("content") or []
    seen: set[str] = set()
    keys: list[str] = []
    for node in content:
        if node.get("type") != "blockCard":
            continue
        url = (node.get("attrs") or {}).get("url") or ""
        m = re.search(r"/browse/(PIN-\d+)", url, re.IGNORECASE)
        if m and m.group(1).upper() not in seen:
            seen.add(m.group(1).upper())
            keys.append(m.group(1).upper())
    return keys


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
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Create or append Confluence page (ADF) via REST API v2")
    parser.add_argument("--title", "-t", required=True, help="Page title")
    parser.add_argument("--jira-url", "-j", default="", help="Jira issue URL for blockCard (optional)")
    parser.add_argument("--body-json", "-b", default="", help="Full ADF JSON string")
    parser.add_argument("--body-file", default="", help="Path to ADF JSON file (relative → repo tmp/)")
    parser.add_argument("--body-stdin", action="store_true", help="Read ADF JSON from stdin")
    parser.add_argument(
        "--unlink-issues",
        default="",
        help="Jira issue keys to unlink from this page (comma-separated). Default: auto-detect PIN-* from body blockCards.",
    )
    parser.add_argument(
        "--no-unlink",
        action="store_true",
        help="Do not remove remotelink from PINs after publish (disable default unlink).",
    )
    parser.add_argument(
        "--output-file",
        default="",
        help="Optional: write operation summary JSON to file.",
    )
    args = parser.parse_args()

    token = os.environ.get("ATLASSIAN_API_TOKEN")
    if not token:
        print("Error: Set ATLASSIAN_API_TOKEN.", file=sys.stderr)
        sys.exit(1)

    try:
        profile = load_atlassian_profile(PROFILE_PATH)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    base_url = profile["base_url"]
    space_id = profile["space_id"]
    parent_id = profile["parent_id"]
    email = profile["email"]
    if not all([base_url, space_id, parent_id]):
        print("Error: Profile must set confluence_base_url, confluence_space_id, confluence_parent_id.", file=sys.stderr)
        sys.exit(1)
    if not email:
        print("Error: Set CONFLUENCE_EMAIL or me.email in profile.", file=sys.stderr)
        sys.exit(1)

    auth = basic_auth(email, token)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    new_adf_raw = build_adf_from_args(args, TMP_DIR)
    new_adf = json.loads(new_adf_raw) if isinstance(new_adf_raw, str) else new_adf_raw
    new_content = new_adf.get("content") or []

    existing = find_page_by_title(base_url, auth, space_id, args.title)
    page_id = None
    page_url_out = ""
    action = "created"
    if existing:
        action = "updated"
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
        path = webui if webui.startswith("/") else ("/" + webui) if webui else ""
        if path.startswith("/spaces/") and not path.startswith("/wiki/"):
            path = "/wiki" + path
        page_url_out = (base_url.rstrip("/") + path) if path else ""
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
        path = webui if webui.startswith("/") else ("/" + webui) if webui else ""
        if path.startswith("/spaces/") and not path.startswith("/wiki/"):
            path = "/wiki" + path
        page_url_out = (base_url.rstrip("/") + path) if path else ""

    if page_id is not None:
        page_info = {"page_id": str(page_id), "url": page_url_out, "title": args.title}
        page_info_path = TMP_DIR / "confluence_page_latest.json"
        with open(page_info_path, "w", encoding="utf-8") as f:
            json.dump(page_info, f, ensure_ascii=False, indent=2)

    unlink_list = args.unlink_issues if args.unlink_issues else (
        ",".join(extract_pin_keys_from_adf(new_adf)) if not args.no_unlink else ""
    )
    unlink_total = 0
    unlink_deleted = 0
    unlink_errors = 0
    unlink_detail: list[dict[str, str]] = []
    if page_id and unlink_list:
        issue_keys = [k.strip() for k in unlink_list.split(",") if k.strip()]
        if issue_keys:
            unlink_total = len(issue_keys)
            for key in issue_keys:
                try:
                    deleted = delete_remotelink_for_confluence_page(base_url, auth, key, str(page_id))
                    if deleted:
                        unlink_deleted += 1
                        unlink_detail.append({"key": key, "status": "unlinked"})
                    else:
                        unlink_detail.append({"key": key, "status": "no_link"})
                except Exception as e:
                    unlink_errors += 1
                    unlink_detail.append({"key": key, "status": "error", "message": str(e)})

    op_summary = {
        "ok": unlink_errors == 0,
        "action": action,
        "page_id": str(page_id) if page_id is not None else "",
        "url": page_url_out,
        "title": args.title,
        "unlink_total": unlink_total,
        "unlink_deleted": unlink_deleted,
        "unlink_errors": unlink_errors,
        "unlink_detail": unlink_detail,
    }
    op_path = None
    if args.output_file:
        op_path = Path(args.output_file)
        if not op_path.is_absolute():
            op_path = REPO_ROOT / op_path
        op_path.parent.mkdir(parents=True, exist_ok=True)
        op_path.write_text(json.dumps(op_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if op_path:
        print(
            "DONE confluence_create_page "
            f"action={action} page_id={op_summary['page_id']} unlink_deleted={unlink_deleted} "
            f"unlink_errors={unlink_errors} output={op_path}"
        )
    else:
        print(
            "DONE confluence_create_page "
            f"action={action} page_id={op_summary['page_id']} unlink_deleted={unlink_deleted} "
            f"unlink_errors={unlink_errors}"
        )
    if unlink_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
