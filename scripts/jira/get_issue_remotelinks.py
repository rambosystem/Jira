#!/usr/bin/env python3
"""GET /rest/api/3/issue/{issueIdOrKey}/remotelink - list remote links (e.g. Wiki) for a Jira issue."""
import argparse
import base64
import json
import os
import re
import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
PROFILE_PATH = REPO_ROOT / "Assets" / "Global" / "profile.yaml"
ENV_PATH = REPO_ROOT / ".env"


def _ssl_context():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    return ctx


def load_dotenv():
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


def profile_value(text: str, key: str) -> str:
    m = re.search(
        rf"^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'#\n]+)[\"']?\s*(?:#|$)",
        text,
        re.MULTILINE,
    )
    return m.group(1).strip().strip('"').strip("'") if m else ""


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Get remote links for a Jira issue")
    parser.add_argument("issue", nargs="?", default="PIN-2805", help="Issue key, e.g. PIN-2805")
    args = parser.parse_args()

    if not PROFILE_PATH.is_file():
        print(f"Error: Profile not found: {PROFILE_PATH}", file=sys.stderr)
        return 1
    text = PROFILE_PATH.read_text(encoding="utf-8")
    base_url = profile_value(text, "confluence_base_url")
    email = profile_value(text, "email") or os.environ.get("CONFLUENCE_EMAIL", "")
    token = os.environ.get("ATLASSIAN_API_TOKEN", "")
    if not base_url:
        print("Error: confluence_base_url not in profile.", file=sys.stderr)
        return 1
    if not email or not token:
        print("Error: need email (profile or CONFLUENCE_EMAIL) and ATLASSIAN_API_TOKEN.", file=sys.stderr)
        return 1

    base_url = base_url.rstrip("/")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    url = f"{base_url}/rest/api/3/issue/{args.issue}/remotelink"
    req = Request(url, headers={"Accept": "application/json", "Authorization": f"Basic {auth}"})
    try:
        with urlopen(req, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error {e.code}: {body}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
