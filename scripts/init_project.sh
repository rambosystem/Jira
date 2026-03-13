#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Interactive project initializer.

Flow:
1) Username
2) Email
3) Team Name (e.g. Defenders)
4) Confluence Folder URL (report root)
5) ATLASSIAN_API_TOKEN

Then script calls Atlassian APIs to auto-generate profile.yaml + .env.

Usage:
  bash scripts/init_project.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE_PATH="$REPO_ROOT/config/assets/global/profile.yaml"
ENV_PATH="$REPO_ROOT/.env"

mkdir -p "$(dirname "$PROFILE_PATH")"
touch "$ENV_PATH"

upsert_env() {
  local key="$1"
  local value="$2"
  local tmp
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    BEGIN { done = 0 }
    $0 ~ "^" k "=" {
      print k "=" v
      done = 1
      next
    }
    { print }
    END { if (!done) print k "=" v }
  ' "$ENV_PATH" > "$tmp"
  mv "$tmp" "$ENV_PATH"
}

require_non_empty() {
  local name="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    echo "Error: $name cannot be empty." >&2
    exit 1
  fi
}

echo "Step 1/5 - Username"
read -r -p "Input username: " USERNAME
require_non_empty "username" "$USERNAME"

echo "Step 2/5 - Email"
read -r -p "Input email: " EMAIL
require_non_empty "email" "$EMAIL"

echo "Step 3/5 - Team Name"
read -r -p 'Input team name (e.g. "Defenders"): ' TEAM_NAME
require_non_empty "team name" "$TEAM_NAME"

echo "Step 4/5 - Confluence Folder URL"
read -r -p "Input Confluence Folder URL (report root): " CONFLUENCE_FOLDER_URL
require_non_empty "Confluence Folder URL" "$CONFLUENCE_FOLDER_URL"

echo "Step 5/5 - ATLASSIAN_API_TOKEN"
read -r -s -p "Input ATLASSIAN_API_TOKEN: " ATLASSIAN_API_TOKEN
echo
require_non_empty "ATLASSIAN_API_TOKEN" "$ATLASSIAN_API_TOKEN"

PARSED="$(python3 - "$CONFLUENCE_FOLDER_URL" <<'PY'
import re
import sys
from urllib.parse import urlparse

url = sys.argv[1].strip()
u = urlparse(url)
if not u.scheme or not u.netloc:
    print("ERR|Invalid Confluence Folder URL")
    raise SystemExit(0)

base_url = f"{u.scheme}://{u.netloc}"
m = re.search(r"/spaces/([^/]+)/folder/(\d+)", u.path)
if not m:
    print("ERR|URL must look like /wiki/spaces/{space_key}/folder/{parent_id}")
    raise SystemExit(0)

space_key = m.group(1)
parent_id = m.group(2)
print(f"OK|{base_url}|{space_key}|{parent_id}")
PY
)"

if [[ "$PARSED" == ERR* ]]; then
  echo "Error: ${PARSED#ERR|}" >&2
  exit 1
fi

IFS='|' read -r _ CONFLUENCE_BASE_URL CONFLUENCE_SPACE_KEY CONFLUENCE_PARENT_ID <<< "$PARSED"
CONFLUENCE_SPACE_KEY_ENCODED="$(python3 - "$CONFLUENCE_SPACE_KEY" <<'PY'
import sys
from urllib.parse import quote
print(quote(sys.argv[1], safe=""))
PY
)"

AUTH_B64="$(printf '%s' "${EMAIL}:${ATLASSIAN_API_TOKEN}" | base64 | tr -d '\n')"

MYSELF_JSON="$(curl -fsS \
  -H "Accept: application/json" \
  -H "Authorization: Basic $AUTH_B64" \
  "$CONFLUENCE_BASE_URL/rest/api/3/myself")"

ACCOUNT_INFO="$(python3 - "$MYSELF_JSON" <<'PY'
import json
import sys
obj = json.loads(sys.argv[1])
account_id = obj.get("accountId", "")
display_name = obj.get("displayName", "")
print(f"{account_id}|{display_name}")
PY
)"
IFS='|' read -r ACCOUNT_ID DISPLAY_NAME_API <<< "$ACCOUNT_INFO"
require_non_empty "account_id (from /rest/api/3/myself)" "$ACCOUNT_ID"

SPACE_JSON="$(curl -fsS \
  -H "Accept: application/json" \
  -H "Authorization: Basic $AUTH_B64" \
  "$CONFLUENCE_BASE_URL/wiki/api/v2/spaces?keys=$CONFLUENCE_SPACE_KEY_ENCODED&limit=1")"

CONFLUENCE_SPACE_ID="$(python3 - "$SPACE_JSON" <<'PY'
import json
import sys
obj = json.loads(sys.argv[1])
results = obj.get("results") or []
if not results:
    print("")
else:
    print(str(results[0].get("id", "")))
PY
)"
require_non_empty "confluence_space_id (from /wiki/api/v2/spaces)" "$CONFLUENCE_SPACE_ID"

DISPLAY_NAME="${DISPLAY_NAME_API:-$USERNAME}"

cat > "$PROFILE_PATH" <<EOF
me:
  name: $USERNAME
  display_name: $DISPLAY_NAME
  email: $EMAIL
  account_id: "$ACCOUNT_ID"
  team: $TEAM_NAME
  confluence_workspace: "$CONFLUENCE_FOLDER_URL"
  confluence_base_url: "$CONFLUENCE_BASE_URL"
  confluence_space_key: "$CONFLUENCE_SPACE_KEY"
  confluence_parent_id: "$CONFLUENCE_PARENT_ID"
  confluence_space_id: "$CONFLUENCE_SPACE_ID"
EOF

upsert_env EMAIL "$EMAIL"
upsert_env CONFLUENCE_EMAIL "$EMAIL"
upsert_env ATLASSIAN_API_TOKEN "$ATLASSIAN_API_TOKEN"
upsert_env ACCOUNT_ID "$ACCOUNT_ID"
upsert_env CONFLUENCE_BASE_URL "$CONFLUENCE_BASE_URL"
upsert_env CONFLUENCE_SPACE_KEY "$CONFLUENCE_SPACE_KEY"
upsert_env CONFLUENCE_PARENT_ID "$CONFLUENCE_PARENT_ID"
upsert_env CONFLUENCE_SPACE_ID "$CONFLUENCE_SPACE_ID"

chmod 600 "$ENV_PATH" || true

echo "Initialization completed."
echo "Generated: $PROFILE_PATH"
echo "Updated:   $ENV_PATH"
