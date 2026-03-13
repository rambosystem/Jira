#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.jira_issue_flow import assemble_issue_plan, resolve_output_path, write_output

ENV_PATH = REPO_ROOT / ".env"


def load_spec(args: argparse.Namespace) -> dict:
    if args.spec_json:
        return json.loads(args.spec_json)
    if args.spec_file:
        spec_path = Path(args.spec_file)
        if not spec_path.is_absolute():
            spec_path = REPO_ROOT / spec_path
        return json.loads(spec_path.read_text(encoding="utf-8"))
    raise RuntimeError("Provide --spec-json or --spec-file.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble a Jira issue plan from structured spec JSON.")
    parser.add_argument("--spec-json", default="", help="Inline spec JSON.")
    parser.add_argument("--spec-file", default="", help="Path to spec JSON file.")
    parser.add_argument("--skip-duplicate-check", action="store_true", help="Do not query duplicates during plan assembly.")
    parser.add_argument("--output-file", default="", help="Optional: write assembled plan JSON to file.")
    args = parser.parse_args()

    try:
        spec = load_spec(args)
        plan = assemble_issue_plan(REPO_ROOT, ENV_PATH, spec, check_duplicates=not args.skip_duplicate_check)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_path = resolve_output_path(REPO_ROOT, args.output_file)
    write_output(out_path, plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if out_path:
        print(f"DONE assemble_jira_issue output={out_path}")
    else:
        print("DONE assemble_jira_issue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
