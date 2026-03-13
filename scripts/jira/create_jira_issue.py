#!/usr/bin/env python3
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
from scripts.common.jira_issue_flow import execute_issue_plan, load_token, resolve_output_path, write_output

ENV_PATH = REPO_ROOT / ".env"


def load_plan(args: argparse.Namespace) -> dict:
    if args.plan_json:
        return json.loads(args.plan_json)
    if args.plan_file:
        plan_path = Path(args.plan_file)
        if not plan_path.is_absolute():
            plan_path = REPO_ROOT / plan_path
        return json.loads(plan_path.read_text(encoding="utf-8"))
    raise RuntimeError("Provide --plan-json or --plan-file.")


def main() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Create a Jira issue from a pre-assembled plan JSON.")
    parser.add_argument("--plan-json", default="", help="Inline plan JSON.")
    parser.add_argument("--plan-file", default="", help="Path to plan JSON file.")
    parser.add_argument("--skip-post-check", action="store_true", help="Do not fetch the created issue after submit.")
    parser.add_argument("--output-file", default="", help="Optional: write full execution result to file.")
    args = parser.parse_args()

    try:
        plan = load_plan(args)
        token = load_token()
        result = execute_issue_plan(plan, token, fetch_post_check=not args.skip_post_check)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: create_jira_issue failed ({exc.code}): {body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Error: create_jira_issue network failure: {exc}", file=sys.stderr)
        return 1

    out_path = resolve_output_path(REPO_ROOT, args.output_file)
    write_output(out_path, result)
    issue_key = (((result.get("post_check") or {}).get("key")) or ((result.get("created") or {}).get("key")) or "")
    if out_path:
        print(f"DONE create_jira_issue key={issue_key} output={out_path}")
    else:
        print(f"DONE create_jira_issue key={issue_key}")
    return 0 if not result.get("pin_link_failures") else 1


if __name__ == "__main__":
    sys.exit(main())
