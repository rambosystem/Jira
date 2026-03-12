#!/usr/bin/env python3
"""
Unlink all PINs in tmp/pin_analysis.json from the Confluence page saved in tmp/confluence_page_latest.json.
Uses the page_id written by scripts/confluence/confluence_create_page.py so no manual ID is needed.

Usage:
  python scripts/pin/unlink_pins_from_latest_page.py
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth
from scripts.common.env import load_dotenv
from scripts.common.jira_remotelinks import delete_remotelink_for_confluence_page
from scripts.common.profile import load_atlassian_profile, resolve_profile_path

TMP_DIR = REPO_ROOT / "tmp"
PAGE_INFO_FILE = TMP_DIR / "confluence_page_latest.json"
PIN_ANALYSIS_FILE = TMP_DIR / "pin_analysis.json"
PROFILE_PATH = resolve_profile_path(REPO_ROOT)
ENV_PATH = REPO_ROOT / ".env"


def main() -> int:
    load_dotenv(ENV_PATH)
    if not PAGE_INFO_FILE.is_file():
        print(
            f"Error: {PAGE_INFO_FILE} not found. Publish a Confluence page first (scripts/confluence/confluence_create_page.py).",
            file=sys.stderr,
        )
        return 1
    if not PIN_ANALYSIS_FILE.is_file():
        print(
            f"Error: {PIN_ANALYSIS_FILE} not found. Generate a PIN report first (scripts/pin/request_pin_report_json.py).",
            file=sys.stderr,
        )
        return 1

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

    page_info = json.loads(PAGE_INFO_FILE.read_text(encoding="utf-8"))
    page_id = page_info.get("page_id") or page_info.get("id")
    if not page_id:
        print("Error: confluence_page_latest.json has no page_id.", file=sys.stderr)
        return 1

    analysis = json.loads(PIN_ANALYSIS_FILE.read_text(encoding="utf-8"))
    pin_ids = analysis.get("pin_ids") or []
    if not pin_ids:
        print("Error: pin_analysis.json has no pin_ids.", file=sys.stderr)
        return 1

    max_workers = min(10, max(1, len(pin_ids)))
    print(f"Unlinking {len(pin_ids)} PINs from Confluence page {page_id} (concurrent, max_workers={max_workers})", file=sys.stderr)

    def unlink_one(key: str) -> tuple[str, bool, str]:
        try:
            deleted = delete_remotelink_for_confluence_page(base_url, auth, key, str(page_id))
            return (key, deleted, "")
        except Exception as e:
            return (key, False, str(e))

    ok = 0
    err = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(unlink_one, key): key for key in pin_ids}
        for fut in as_completed(futures):
            key, deleted, msg = fut.result()
            if deleted:
                print(f"Unlinked {key} from page {page_id}")
                ok += 1
            elif msg:
                print(f"Warning: {key}: {msg}", file=sys.stderr)
                err += 1

    print(f"Done: {ok} unlinked, {len(pin_ids) - ok - err} had no link, {err} errors.", file=sys.stderr)
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
