#!/usr/bin/env python3
"""
Unlink all PINs in tmp/pin_analysis.json from the Confluence page saved in tmp/confluence_page_latest.json.
Uses the page_id written by confluence_create_page.py so no manual ID is needed.

Usage:
  python scripts/unlink_pins_from_latest_page.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TMP_DIR = REPO_ROOT / "tmp"
PAGE_INFO_FILE = TMP_DIR / "confluence_page_latest.json"
PIN_ANALYSIS_FILE = TMP_DIR / "pin_analysis.json"
DELETE_SCRIPT = SCRIPT_DIR / "delete_issue_remotelink.py"


def main() -> int:
    if not PAGE_INFO_FILE.is_file():
        print(f"Error: {PAGE_INFO_FILE} not found. Publish a Confluence page first (confluence_create_page.py).", file=sys.stderr)
        return 1
    if not PIN_ANALYSIS_FILE.is_file():
        print(f"Error: {PIN_ANALYSIS_FILE} not found. Generate a PIN report first (request_pin_report_json.py).", file=sys.stderr)
        return 1

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
            r = subprocess.run(
                [sys.executable, str(DELETE_SCRIPT), "--issue", key, "--confluence-page-id", str(page_id)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0 and "Deleted" in (r.stdout or ""):
                return (key, True, "")
            if r.returncode != 0 and r.stderr:
                return (key, False, r.stderr.strip())
            return (key, False, "")
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
