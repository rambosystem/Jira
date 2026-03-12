#!/usr/bin/env python3
"""Build policy JSON bundle from YAML/config sources."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.policy_bundle import build_policy_bundle, write_policy_bundle


def main() -> int:
    try:
        bundle = build_policy_bundle(REPO_ROOT)
        out = write_policy_bundle(REPO_ROOT, bundle)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "output": str(out),
                "generated_at": bundle.get("generated_at"),
                "projects": bundle.get("projects"),
                "source_count": len(bundle.get("sources") or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
