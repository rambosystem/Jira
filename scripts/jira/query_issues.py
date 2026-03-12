#!/usr/bin/env python3
"""Query Jira issues with raw JQL only."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth, jira_api_v3_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.ticket_config import load_jira_runtime_profile

ENV_PATH = REPO_ROOT / ".env"
def _search_jira(base_url: str, auth: str, jql: str, fields: list[str], limit: int) -> dict[str, Any]:
    url = jira_api_v3_url(base_url, "/search/jql")
    payload = {"jql": jql, "maxResults": limit, "fields": fields}
    return request_json(
        url,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        data=payload,
        insecure_env_var="JIRA_INSECURE_SSL",
    )


def _table_rows(issues: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for issue in issues:
        fields = issue.get("fields") or {}
        rows.append(
            {
                "key": issue.get("key", ""),
                "status": (fields.get("status") or {}).get("name", ""),
                "assignee": (fields.get("assignee") or {}).get("displayName", ""),
                "priority": (fields.get("priority") or {}).get("name", ""),
                "summary": fields.get("summary", ""),
            }
        )
    return rows


def _print_table(rows: list[dict[str, str]]) -> None:
    headers = ["key", "status", "assignee", "priority", "summary"]
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            widths[h] = max(widths[h], len(row.get(h, "")))
    line = " | ".join(h.ljust(widths[h]) for h in headers)
    sep = "-+-".join("-" * widths[h] for h in headers)
    print(line)
    print(sep)
    for row in rows:
        print(" | ".join(row.get(h, "").ljust(widths[h]) for h in headers))


def run() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Query Jira using raw JQL.")
    parser.add_argument("--jql", required=True, help="Raw JQL query.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--fields",
        default="key,summary,status,assignee,priority,components,parent,created",
        help="Comma-separated Jira fields.",
    )
    parser.add_argument("--format", default="json", choices=["table", "json"])
    parser.add_argument("--dry-run", action="store_true", help="Resolve payload only, no Jira request.")
    parser.add_argument(
        "--output-file",
        default="",
        help="Optional: write full result JSON to file.",
    )
    args = parser.parse_args()

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    limit = max(1, min(args.limit, 100))

    if args.dry_run:
        payload = {
            "ok": True,
            "mode": "dry_run",
            "jql": args.jql.strip(),
            "limit": limit,
            "fields": fields,
        }
        if args.output_file:
            out = Path(args.output_file)
            if not out.is_absolute():
                out = REPO_ROOT / out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            print(f"DONE query_issues dry_run=true output={out}")
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            print("DONE query_issues dry_run=true")
        return 0

    try:
        profile = load_jira_runtime_profile(REPO_ROOT)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    token = os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
    if not token:
        print("Error: ATLASSIAN_API_TOKEN not set.", file=sys.stderr)
        return 1
    auth = basic_auth(profile["email"], token)

    try:
        data = _search_jira(profile["base_url"], auth, args.jql.strip(), fields, limit)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: Jira query failed ({exc.code}): {body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Error: Jira query failed (network): {exc}", file=sys.stderr)
        return 1

    issues = data.get("issues") or []
    result = {
        "ok": True,
        "mode": "query",
        "jql": args.jql.strip(),
        "limit": limit,
        "fields": fields,
        "total": len(issues),
        "issues": issues,
    }
    out = None
    if args.output_file:
        out = Path(args.output_file)
        if not out.is_absolute():
            out = REPO_ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.format == "table":
        rows = _table_rows(issues)
        _print_table(rows)
    if out:
        print(f"DONE query_issues total={len(issues)} output={out}")
    else:
        print(f"DONE query_issues total={len(issues)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
