#!/usr/bin/env python3
"""
Get footer and inline comments for a Confluence page via REST API v2.
Uses profile (confluence_base_url) and CONFLUENCE_EMAIL + ATLASSIAN_API_TOKEN.

Usage:
  python scripts/confluence/confluence_get_page_comments.py <page_id>
  python scripts/confluence/confluence_get_page_comments.py 1287880712
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth, confluence_api_v2_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.profile import load_atlassian_profile, resolve_profile_path

PROFILE_PATH = resolve_profile_path(REPO_ROOT)
ENV_PATH = REPO_ROOT / ".env"


def _ensure_utf8_stdout() -> None:
    """Force stdout to UTF-8 so Chinese and other Unicode display correctly (e.g. on Windows)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _decode_text(s: str) -> str:
    """Decode text; fix mojibake when UTF-8 was misinterpreted as Latin-1/CP1252."""
    if not s or not isinstance(s, str):
        return s
    # If string looks like UTF-8 bytes decoded as Latin-1, re-encode and decode as UTF-8
    try:
        repaired = s.encode("latin-1").decode("utf-8")
        if repaired != s and "\uFFFD" not in repaired:
            return repaired
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return s


def _parse_comment_body(c: dict[str, Any]) -> str:
    """Extract plain text from comment body (atlas_doc_format ADF)."""
    body_obj = (c.get("body") or {}).get("atlas_doc_format")
    if not isinstance(body_obj, dict):
        body_obj = {}
    raw_value = body_obj.get("value")
    if isinstance(raw_value, dict) and "content" in raw_value:
        adf = raw_value
    elif isinstance(body_obj, dict) and "content" in body_obj:
        adf = body_obj
    elif isinstance(raw_value, str) and raw_value.strip():
        try:
            adf = json.loads(raw_value)
        except json.JSONDecodeError:
            return _decode_text(raw_value[:300] + ("..." if len(raw_value) > 300 else ""))
    else:
        return "(no content)"
    text_parts = []
    for node in (adf.get("content") or []):
        if node.get("type") == "paragraph":
            for item in (node.get("content") or []):
                if item.get("type") == "text":
                    text_parts.append(_decode_text((item.get("text") or "").strip()))
        elif node.get("type") == "heading":
            for item in (node.get("content") or []):
                if item.get("type") == "text":
                    text_parts.append(_decode_text((item.get("text") or "").strip()))
    raw = " ".join(text_parts).strip() or "(no text)"
    return _decode_text(raw)


def _comment_to_item(c: dict[str, Any], include_commented_text: bool = False) -> dict[str, Any]:
    """Build {author, created, body, commented_text?} from API comment object."""
    version = c.get("version") or {}
    created = version.get("createdAt") or c.get("createdAt") or ""
    author = (
        (c.get("createdBy") or {}).get("displayName")
        or (c.get("createdBy") or {}).get("publicName")
        or version.get("authorId")
        or "Unknown"
    )
    body = _parse_comment_body(c)
    item: dict[str, Any] = {"author": author, "created": created, "body": body}
    if include_commented_text:
        props = c.get("properties") or {}
        selected = props.get("inlineOriginalSelection")
        if selected and isinstance(selected, str):
            item["commented_text"] = _decode_text(selected.strip())
        elif selected:
            item["commented_text"] = str(selected).strip()
    return item


def _fetch_comments(
    base_url: str,
    auth: str,
    path: str,
    extra_params: list[str] | None = None,
    include_commented_text: bool = False,
) -> list[dict[str, Any]]:
    params = ["limit=50", "body-format=atlas_doc_format"]
    if extra_params:
        params.extend(extra_params)
    url = confluence_api_v2_url(
        base_url, f"{path}?{'&'.join(params)}"
    )
    data = request_json(
        url,
        method="GET",
        headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
        insecure_env_var="CONFLUENCE_INSECURE_SSL",
    )
    results = data.get("results") or []
    return [_comment_to_item(c, include_commented_text=include_commented_text) for c in results]


def main() -> None:
    _ensure_utf8_stdout()
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Get Confluence page footer and inline comments")
    parser.add_argument("page_id", help="Confluence page ID (e.g. 1287880712)")
    args = parser.parse_args()
    page_id = args.page_id.strip()

    profile = load_atlassian_profile(PROFILE_PATH)
    base_url = profile.get("base_url") or ""
    email = profile.get("email") or ""
    token = os.environ.get("ATLASSIAN_API_TOKEN") or ""
    if not base_url or not email:
        print("ERROR: profile missing confluence_base_url or email", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("ERROR: set ATLASSIAN_API_TOKEN", file=sys.stderr)
        sys.exit(1)
    auth = basic_auth(email, token)
    out = {"footer_comments": [], "inline_comments": []}
    try:
        out["footer_comments"] = _fetch_comments(
            base_url, auth, f"/pages/{page_id}/footer-comments"
        )
        out["inline_comments"] = _fetch_comments(
            base_url,
            auth,
            f"/pages/{page_id}/inline-comments",
            extra_params=["include-properties=true"],
            include_commented_text=True,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not out["footer_comments"] and not out["inline_comments"]:
        print("No comments on this page.")
        return

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
