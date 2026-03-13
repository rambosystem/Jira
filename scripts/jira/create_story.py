#!/usr/bin/env python3
"""Create Jira issues from one structured spec using the new assemble/execute flow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.env import load_dotenv
from scripts.common.jira_issue_flow import (
    assemble_issue_plan,
    execute_issue_plan,
    load_token,
    resolve_output_path,
    write_output,
)

ENV_PATH = REPO_ROOT / ".env"


def build_spec(args: argparse.Namespace) -> dict:
    return {
        "project": args.project,
        "issue_type": args.issue_type,
        "summary": args.summary,
        "components": args.components,
        "description": args.description,
        "priority": args.priority,
        "assignee_account_id": args.assignee_account_id,
        "parent": args.parent,
        "quarter": args.quarter,
        "client_id": args.client_id,
        "story_type": args.story_type,
        "ux_review_required": args.ux_review_required,
        "ux_review_status": args.ux_review_status,
        "technical_story_type": args.technical_story_type,
        "allow_duplicate": args.allow_duplicate,
        "link_pins": args.link_pin,
    }


def run() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(
        description="Assemble and create one Jira issue from a structured spec.",
    )
    parser.add_argument("--project", default="", help="Project key, default from config/assets/global/profile.yaml")
    parser.add_argument("--issue-type", default="Story", help="Jira issue type, e.g. Story, Technical Story, Epic")
    parser.add_argument("--summary", required=True, help="Issue summary/title")
    parser.add_argument("--components", required=True, help="Comma-separated components, e.g. 'SOV,My Report'")
    parser.add_argument("--description", default="", help="Plain text description")
    parser.add_argument("--priority", default="")
    parser.add_argument("--assignee-account-id", default="", help="Atlassian account id override")
    parser.add_argument("--parent", default="", help="Parent issue key override, e.g. CP-45460")
    parser.add_argument("--quarter", default="", help="Quarter token for auto parent match, e.g. 26Q2")
    parser.add_argument("--client-id", default="", help="Client ID override")
    parser.add_argument("--story-type", default="")
    parser.add_argument("--ux-review-required", default="")
    parser.add_argument("--ux-review-status", default="")
    parser.add_argument("--technical-story-type", default="")
    parser.add_argument("--allow-duplicate", action="store_true", help="Create even if similar summary exists")
    parser.add_argument("--link-pin", default="", help="PIN issue keys to link after create, comma-separated.")
    parser.add_argument("--dry-run", action="store_true", help="Only assemble and print the resolved plan")
    parser.add_argument("--output-file", default="", help="Optional: write full result JSON to file.")
    args = parser.parse_args()

    try:
        plan = assemble_issue_plan(REPO_ROOT, ENV_PATH, build_spec(args), check_duplicates=True)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_path = resolve_output_path(REPO_ROOT, args.output_file)
    duplicate_count = int(((plan.get("preflight") or {}).get("duplicate_count")) or 0)
    if duplicate_count and not args.allow_duplicate:
        out = {
            "preflight": plan.get("preflight") or {},
            "blocked": "duplicate_detected",
            "hint": "pass --allow-duplicate to continue",
            "plan": plan,
        }
        write_output(out_path, out)
        if out_path:
            print(f"DONE create_story blocked=duplicate_detected output={out_path}")
        else:
            print("DONE create_story blocked=duplicate_detected")
        return 2

    if args.dry_run:
        write_output(out_path, plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        if out_path:
            print(f"DONE create_story dry_run=true output={out_path}")
        else:
            print("DONE create_story dry_run=true")
        return 0

    try:
        result = execute_issue_plan(plan, load_token(), fetch_post_check=True)
    except RuntimeError as exc:
        out = {"plan": plan, "error": str(exc)}
        write_output(out_path, out)
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        out = {"plan": plan, "error_code": exc.code, "error_body": body}
        write_output(out_path, out)
        print(f"Error: create_story create_failed code={exc.code}", file=sys.stderr)
        return 1
    except URLError as exc:
        out = {"plan": plan, "error": f"create failed (network): {exc}"}
        write_output(out_path, out)
        print("Error: create_story create_failed_network", file=sys.stderr)
        return 1

    write_output(out_path, result)
    issue_key = (((result.get("post_check") or {}).get("key")) or ((result.get("created") or {}).get("key")) or "")
    if out_path:
        print(f"DONE create_story key={issue_key} output={out_path}")
    else:
        print(f"DONE create_story key={issue_key}")
    return 0 if not result.get("pin_link_failures") else 1


if __name__ == "__main__":
    sys.exit(run())
