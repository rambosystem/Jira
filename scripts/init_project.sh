#!/usr/bin/env bash
set -euo pipefail

DEBUG_INIT="${DEBUG_INIT:-0}"

log() {
  printf '[init] %s\n' "$*"
}

fail() {
  printf '[init][error] %s\n' "$*" >&2
}

if [[ "$DEBUG_INIT" == "1" ]]; then
  set -x
fi

on_error() {
  local exit_code="$1"
  local line_no="$2"
  local cmd="$3"
  fail "line $line_no failed with exit code $exit_code"
  fail "command: $cmd"
  exit "$exit_code"
}

trap 'on_error "$?" "$LINENO" "$BASH_COMMAND"' ERR

usage() {
  cat <<'EOF'
Interactive project initializer.

Flow:
1) Email
2) Project name or key (e.g. CP / Commerce Platform)
3) ATLASSIAN_API_TOKEN

Confluence workspace:
- Default to My Space / Workspace
- If Workspace folder does not exist, create it automatically

Then script calls Atlassian APIs to auto-generate:
- config/assets/global/profile.yaml
- config/assets/global/epic-list.yaml
- .env
- config/assets/project/<project>/components.yaml
- config/assets/project/<project>/team.yaml
- config/policy/<project>/ticket-schema.json
- config/policy/field-mappings.yaml

Usage:
  bash scripts/init_project.sh

Debug:
  DEBUG_INIT=1 bash scripts/init_project.sh
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
ATLASSIAN_BASE_URL="https://pacvue-enterprise.atlassian.net"

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
    fail "$name cannot be empty."
    exit 1
  fi
}

echo "Step 1/4 - Email"
read -r -p "Input email: " EMAIL
require_non_empty "email" "$EMAIL"

echo "Step 2/4 - Project Name or Key"
read -r -p 'Input project name or key (e.g. "CP" or "Commerce Platform"): ' PROJECT_INPUT
require_non_empty "project name or key" "$PROJECT_INPUT"

echo "Step 3/3 - ATLASSIAN_API_TOKEN"
read -r -s -p "Input ATLASSIAN_API_TOKEN: " ATLASSIAN_API_TOKEN
echo
require_non_empty "ATLASSIAN_API_TOKEN" "$ATLASSIAN_API_TOKEN"

CONFLUENCE_BASE_URL="$ATLASSIAN_BASE_URL"
AUTH_B64="$(printf '%s' "${EMAIL}:${ATLASSIAN_API_TOKEN}" | base64 | tr -d '\n')"
WORKSPACE_MODE="1"
CONFLUENCE_FOLDER_URL=""

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

MYSELF_JSON_PATH="$TMP_DIR/myself.json"
SPACE_JSON_PATH="$TMP_DIR/space.json"
PROJECT_JSON_PATH="$TMP_DIR/project.json"
COMPONENTS_JSON_PATH="$TMP_DIR/components.json"
ASSIGNABLE_JSON_PATH="$TMP_DIR/assignable.json"
CREATEMETA_JSON_PATH="$TMP_DIR/createmeta.json"
EPICS_JSON_PATH="$TMP_DIR/epics.json"
WORKSPACE_JSON_PATH="$TMP_DIR/workspace.json"

log "Fetching Atlassian identity from /rest/api/3/myself"
curl -fsS \
  -H "Accept: application/json" \
  -H "Authorization: Basic $AUTH_B64" \
  "$CONFLUENCE_BASE_URL/rest/api/3/myself" > "$MYSELF_JSON_PATH"

ACCOUNT_INFO="$(python3 - "$MYSELF_JSON_PATH" <<'PY'
import json
import sys
obj = json.load(open(sys.argv[1], encoding="utf-8"))
account_id = obj.get("accountId", "")
display_name = obj.get("displayName", "")
print(f"{account_id}|{display_name}")
PY
)"
IFS='|' read -r ACCOUNT_ID DISPLAY_NAME_API <<< "$ACCOUNT_INFO"
require_non_empty "account_id (from /rest/api/3/myself)" "$ACCOUNT_ID"
USERNAME="$(python3 - "$EMAIL" "$DISPLAY_NAME_API" <<'PY'
import re
import sys

email = sys.argv[1].strip()
display_name = sys.argv[2].strip()
local = email.split("@", 1)[0] if "@" in email else email
candidate = local or display_name or "user"
candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-")
print(candidate or "user")
PY
)"

log "Resolving Confluence workspace"
python3 - "$CONFLUENCE_BASE_URL" "$AUTH_B64" "$WORKSPACE_MODE" "$CONFLUENCE_FOLDER_URL" "$WORKSPACE_JSON_PATH" "$SPACE_JSON_PATH" <<'PY'
import json
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import ssl

base_url, auth_b64, workspace_mode, folder_url, workspace_json_path, space_json_path = sys.argv[1:]
ctx = ssl.create_default_context()

def get_json(url: str):
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {auth_b64}",
        },
    )
    with urlopen(req, context=ctx) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

def post_json(url: str, data: dict):
    req = Request(
        url,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}",
        },
        method="POST",
    )
    with urlopen(req, context=ctx) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

def resolve_custom_folder(raw_url: str):
    u = urlparse(raw_url.strip())
    if not u.scheme or not u.netloc:
        raise RuntimeError("Invalid Confluence Folder URL")
    m = re.search(r"/spaces/([^/]+)/folder/(\d+)", u.path)
    if not m:
        raise RuntimeError("URL must look like /wiki/spaces/{space_key}/folder/{parent_id}")
    space_key = m.group(1)
    parent_id = m.group(2)
    spaces = get_json(f"{base_url.rstrip('/')}/wiki/api/v2/spaces?keys={quote(space_key, safe='')}&limit=1")
    results = spaces.get("results") or []
    if not results:
        raise RuntimeError(f"Cannot resolve Confluence space id for {space_key}")
    return {
        "workspace_url": raw_url.strip(),
        "space_key": space_key,
        "parent_id": parent_id,
        "space_id": str(results[0].get("id", "")),
    }

def resolve_default_workspace():
    me = get_json(f"{base_url.rstrip('/')}/wiki/rest/api/user/current?expand=personalSpace")
    personal_space = me.get("personalSpace") or {}
    space_key = str(personal_space.get("key") or "")
    space_id = str(personal_space.get("id") or "")
    homepage = personal_space.get("homepage") or {}
    homepage_id = str(homepage.get("id") or "")
    if not space_key or not space_id or not homepage_id:
        raise RuntimeError("Current Confluence user has no resolvable personal space/homepage")

    children = get_json(f"{base_url.rstrip('/')}/wiki/api/v2/pages/{homepage_id}/direct-children?limit=250")
    results = children.get("results") or []
    workspace_folder = None
    for item in results:
        title = str(item.get("title") or "").strip()
        item_type = str(item.get("type") or "").strip().lower()
        if title == "Workspace" and item_type == "folder":
            workspace_folder = item
            break

    if workspace_folder is None:
        workspace_folder = post_json(
            f"{base_url.rstrip('/')}/wiki/api/v2/folders",
            {"title": "Workspace", "spaceId": space_id, "parentId": homepage_id},
        )

    folder_id = str(workspace_folder.get("id") or "")
    if not folder_id:
        raise RuntimeError("Workspace folder creation succeeded but no folder id returned")
    return {
        "workspace_url": f"{base_url.rstrip('/')}/wiki/spaces/{space_key}/folder/{folder_id}",
        "space_key": space_key,
        "parent_id": folder_id,
        "space_id": space_id,
    }

payload = resolve_default_workspace() if workspace_mode != "2" else resolve_custom_folder(folder_url)
with open(workspace_json_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
with open(space_json_path, "w", encoding="utf-8") as fh:
    json.dump({"ok": True}, fh, ensure_ascii=False, indent=2)
PY

WORKSPACE_INFO="$(python3 - "$WORKSPACE_JSON_PATH" <<'PY'
import json
import sys
obj = json.load(open(sys.argv[1], encoding="utf-8"))
print(
    "|".join(
        [
            obj.get("workspace_url", ""),
            obj.get("space_key", ""),
            obj.get("parent_id", ""),
            obj.get("space_id", ""),
        ]
    )
)
PY
)"
IFS='|' read -r CONFLUENCE_WORKSPACE_URL CONFLUENCE_SPACE_KEY CONFLUENCE_PARENT_ID CONFLUENCE_SPACE_ID <<< "$WORKSPACE_INFO"
require_non_empty "confluence_space_key" "$CONFLUENCE_SPACE_KEY"
require_non_empty "confluence_parent_id" "$CONFLUENCE_PARENT_ID"
require_non_empty "confluence_space_id" "$CONFLUENCE_SPACE_ID"

log "Resolving Jira project metadata for $PROJECT_INPUT"
python3 - "$CONFLUENCE_BASE_URL" "$AUTH_B64" "$PROJECT_INPUT" "$PROJECT_JSON_PATH" <<'PY'
import json
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
import ssl

base_url, auth_b64, project_input, output_path = sys.argv[1:]
ctx = ssl.create_default_context()

def get_json(path: str):
    req = Request(
        f"{base_url.rstrip('/')}/rest/api/3{path}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {auth_b64}",
        },
    )
    with urlopen(req, context=ctx) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

project = None
try:
    project = get_json(f"/project/{quote(project_input, safe='')}")
except HTTPError as exc:
    if exc.code != 404:
        raise

if not project:
    data = get_json(f"/project/search?query={quote(project_input, safe='')}&maxResults=50")
    values = data.get("values") or []
    needle = project_input.strip().lower()
    exact = [
        item for item in values
        if str(item.get("key") or "").lower() == needle or str(item.get("name") or "").lower() == needle
    ]
    matches = exact or values
    if len(matches) != 1:
        raise RuntimeError(f"Cannot uniquely resolve project from input: {project_input}")
    project = matches[0]

with open(output_path, "w", encoding="utf-8") as fh:
    json.dump(project, fh, ensure_ascii=False, indent=2)
PY

PROJECT_KEY="$(python3 - "$PROJECT_JSON_PATH" <<'PY'
import json
import sys
obj = json.load(open(sys.argv[1], encoding="utf-8"))
print((obj.get("key") or "").upper())
PY
)"
require_non_empty "resolved project key" "$PROJECT_KEY"

log "Fetching Jira components for $PROJECT_KEY"
curl -fsS \
  -H "Accept: application/json" \
  -H "Authorization: Basic $AUTH_B64" \
  "$CONFLUENCE_BASE_URL/rest/api/3/project/$PROJECT_KEY/components" > "$COMPONENTS_JSON_PATH"

log "Fetching assignable users for $PROJECT_KEY"
curl -fsS \
  -H "Accept: application/json" \
  -H "Authorization: Basic $AUTH_B64" \
  "$CONFLUENCE_BASE_URL/rest/api/3/user/assignable/search?project=$PROJECT_KEY&maxResults=1000" > "$ASSIGNABLE_JSON_PATH"

log "Fetching recent epics for $PROJECT_KEY"
curl -fsS \
  -X POST \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $AUTH_B64" \
  "$CONFLUENCE_BASE_URL/rest/api/3/search/jql" \
  --data "$(python3 - "$PROJECT_KEY" <<'PY'
import json
import sys
project_key = sys.argv[1]
payload = {
    "jql": (
        f'project = {project_key} '
        'AND issuetype = Epic '
        'AND status NOT IN (Done, "Won\'t Do") '
        'AND created >= -24w '
        'ORDER BY created DESC'
    ),
    "maxResults": 50,
    "fields": ["key", "summary", "components"],
}
print(json.dumps(payload, ensure_ascii=False))
PY
)" > "$EPICS_JSON_PATH"

log "Fetching Jira create metadata for $PROJECT_KEY"
python3 - "$CONFLUENCE_BASE_URL" "$AUTH_B64" "$PROJECT_KEY" "$CREATEMETA_JSON_PATH" <<'PY'
import json
import sys
from urllib.request import Request, urlopen
import ssl

base_url, auth_b64, project_key, output_path = sys.argv[1:]

ctx = ssl.create_default_context()

def get_json(path: str):
    req = Request(
        f"{base_url.rstrip('/')}/rest/api/3{path}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {auth_b64}",
        },
    )
    with urlopen(req, context=ctx) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}

itypes_data = get_json(f"/issue/createmeta/{project_key}/issuetypes")
if isinstance(itypes_data, dict) and "issueTypes" in itypes_data:
    itypes = itypes_data["issueTypes"]
elif isinstance(itypes_data, dict) and "values" in itypes_data:
    itypes = itypes_data["values"]
elif isinstance(itypes_data, list):
    itypes = itypes_data
else:
    raise RuntimeError(f"Unexpected createmeta issue types response: {itypes_data!r}")

items = []
for issue_type in itypes:
    issue_type_id = issue_type.get("id")
    if not issue_type_id:
        continue
    fields_data = get_json(f"/issue/createmeta/{project_key}/issuetypes/{issue_type_id}")
    if isinstance(fields_data, dict) and "values" in fields_data:
        fields_page = fields_data["values"]
    elif isinstance(fields_data, dict) and "fields" in fields_data:
        fields_page = fields_data.get("fields", [])
    elif isinstance(fields_data, list):
        fields_page = fields_data
    else:
        fields_page = []

    def field_obj(field: dict):
        options = [str(o.get("value") or o.get("name") or o.get("id") or "") for o in (field.get("allowedValues") or [])]
        return {
            "name": field.get("name", ""),
            "key": field.get("key") or field.get("fieldId") or "",
            "type": (field.get("schema") or {}).get("type", ""),
            "options": [opt for opt in options if opt],
        }

    items.append(
        {
            "issue_type_id": str(issue_type_id),
            "issue_type": issue_type.get("name", ""),
            "required_fields": [field_obj(f) for f in fields_page if f.get("required")],
            "optional_fields": [field_obj(f) for f in fields_page if not f.get("required")],
        }
    )

result = {
    "ok": True,
    "project": project_key,
    "issue_types": [it.get("name") for it in itypes],
    "items": items,
}
with open(output_path, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=2)
PY

log "Building project discovery payload"
DISCOVERY_JSON="$(python3 - "$PROJECT_JSON_PATH" "$COMPONENTS_JSON_PATH" "$ASSIGNABLE_JSON_PATH" "$CREATEMETA_JSON_PATH" "$EPICS_JSON_PATH" "$PROJECT_KEY" "$EMAIL" "$ACCOUNT_ID" "$USERNAME" <<'PY'
import json
import sys

project_path, components_path, assignable_path, createmeta_path, epics_path, project_key, email, account_id, username = sys.argv[1:]
project = json.load(open(project_path, encoding="utf-8"))
components_data = json.load(open(components_path, encoding="utf-8"))
assignable = json.load(open(assignable_path, encoding="utf-8"))
createmeta = json.load(open(createmeta_path, encoding="utf-8"))
epics_data = json.load(open(epics_path, encoding="utf-8"))

project_name = project.get("name") or project_key
components = sorted(
    [{"name": item.get("name", "").strip()} for item in (components_data or []) if item.get("name", "").strip()],
    key=lambda x: x["name"].lower(),
)

def preferred_default(name: str, options: list[str]) -> str:
    preferred = {
        "Priority": ["Medium", "High", "Highest", "Low"],
        "Story Type": ["Improvement", "New Feature", "API Integration & Enablement"],
        "UX Review Required?": ["No", "Yes"],
        "UX Review Status": ["Not Needed", "Pending", "Reviewed"],
        "Technical Story Type": ["Code Quality", "Architecture", "Others"],
    }
    for candidate in preferred.get(name, []):
        if candidate in options:
            return candidate
    return ""

issue_types = {}
supported_work_types = []
for item in createmeta.get("items", []):
    issue_type = item.get("issue_type", "")
    supported_work_types.append(issue_type)
    required_fields = []
    optional_fields = []
    field_options = {}
    field_defaults = {}
    key_aliases = {}

    for bucket_name, target in (("required_fields", required_fields), ("optional_fields", optional_fields)):
        for field in item.get(bucket_name, []):
            field_name = field.get("name", "").strip()
            if field_name:
                target.append(field_name)
            options = [str(opt) for opt in field.get("options", []) if str(opt)]
            if options:
                field_options[field_name] = options
            default_value = preferred_default(field_name, options)
            if field_name == "Client ID":
                default_value = "0000"
            if default_value:
                field_defaults[field_name] = default_value
            key_aliases[field_name] = field.get("key", "")

    issue_types[issue_type] = {
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "field_options": field_options,
        "field_defaults": field_defaults,
        "_field_keys": key_aliases,
    }

defaults = {
    "client_id": "0000",
    "assignee": {
        "name": username,
        "account_id": account_id,
        "role": "",
    },
}
if "Epic" in supported_work_types:
    defaults["assignee_by_work_type"] = {
        "Epic": {
            "name": username,
            "account_id": account_id,
            "role": "",
        }
    }

field_alias_rules = {
    "Story": {
        "Client ID": "client_id",
        "Story Type": "story_type",
        "UX Review Required?": "ux_review_required",
        "UX Review Status": "ux_review_status",
    },
    "Technical Story": {
        "Client ID": "client_id",
        "Technical Story Type": "technical_story_type",
    },
}
field_mapping_project = {}
for issue_type, aliases in field_alias_rules.items():
    if issue_type not in issue_types:
        continue
    fields = {}
    for field_name, alias in aliases.items():
        key = issue_types[issue_type]["_field_keys"].get(field_name, "")
        if key:
            fields[alias] = key
    if fields:
        field_mapping_project[issue_type] = {"fields": fields}

candidate_members = []
seen = set()
for user in assignable or []:
    user_account_id = (user.get("accountId") or "").strip()
    user_email = (user.get("emailAddress") or "").strip()
    if not user_account_id or user_account_id in seen:
        continue
    seen.add(user_account_id)
    candidate_members.append(
        {
            "name": (user.get("displayName") or user_email or user_account_id).strip(),
            "email": user_email,
            "account_id": user_account_id,
            "selected": user_account_id == account_id or (user_email and user_email.lower() == email.lower()),
        }
    )

payload = {
    "project_key": project_key,
    "project_name": project_name,
    "projects_responsible": [project_key],
    "default_project": project_key,
    "components": components,
    "candidate_members": candidate_members,
    "ticket_schema": {
        "schema_version": 1,
        "supported_work_types": supported_work_types,
        "defaults": defaults,
        "issue_types": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in issue_types.items()},
    },
    "field_mapping_project": field_mapping_project,
    "recent_epics": [
        {
            "key": issue.get("key", ""),
            "title": ((issue.get("fields") or {}).get("summary") or "").strip(),
            "components": [
                (component.get("name") or "").strip()
                for component in (((issue.get("fields") or {}).get("components")) or [])
                if (component.get("name") or "").strip()
            ],
        }
        for issue in (epics_data.get("issues") or [])
        if issue.get("key") and ((issue.get("fields") or {}).get("summary") or "").strip()
    ],
}
print(json.dumps(payload, ensure_ascii=False))
PY
)"
require_non_empty "project discovery payload" "$DISCOVERY_JSON"

PROJECT_NAME="$(python3 - "$DISCOVERY_JSON" <<'PY'
import json
import sys
obj = json.loads(sys.argv[1])
print(obj["project_name"])
PY
)"
DISPLAY_NAME="${DISPLAY_NAME_API:-$USERNAME}"
DEFAULT_PROJECT="$PROJECT_KEY"

PROJECT_DIR="$REPO_ROOT/config/assets/project/$PROJECT_KEY"
POLICY_DIR="$REPO_ROOT/config/policy/$PROJECT_KEY"
mkdir -p "$PROJECT_DIR" "$POLICY_DIR"

log "Writing profile, team, components, schema, field mapping, and epic list"
python3 - "$DISCOVERY_JSON" "$PROFILE_PATH" "$PROJECT_DIR" "$POLICY_DIR" "$USERNAME" "$DISPLAY_NAME" "$EMAIL" "$ACCOUNT_ID" "$DEFAULT_PROJECT" "$CONFLUENCE_WORKSPACE_URL" "$CONFLUENCE_BASE_URL" "$CONFLUENCE_SPACE_KEY" "$CONFLUENCE_PARENT_ID" "$CONFLUENCE_SPACE_ID" <<'PY'
import json
import re
import sys
from pathlib import Path

(
    discovery_json,
    profile_path,
    project_dir,
    policy_dir,
    username,
    display_name,
    email,
    account_id,
    default_project,
    confluence_workspace,
    confluence_base_url,
    confluence_space_key,
    confluence_parent_id,
    confluence_space_id,
) = sys.argv[1:]

discovery = json.loads(discovery_json)
profile_path = Path(profile_path)
project_dir = Path(project_dir)
policy_dir = Path(policy_dir)
project_key = discovery["project_key"]
project_name = discovery["project_name"]

def render_scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(ch in text for ch in [":", "#", "[", "]", "{", "}", '"', "'"]) or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text

def dump_yaml(obj, indent=0):
    lines = []
    prefix = " " * indent
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(dump_yaml(value, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {render_scalar(value)}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                if not item:
                    lines.append(f"{prefix}- {{}}")
                    continue
                first = True
                for key, value in item.items():
                    item_prefix = f"{prefix}- " if first else f"{prefix}  "
                    if isinstance(value, (dict, list)):
                        lines.append(f"{item_prefix}{key}:")
                        lines.extend(dump_yaml(value, indent + 4))
                    else:
                        lines.append(f"{item_prefix}{key}: {render_scalar(value)}")
                    first = False
            else:
                lines.append(f"{prefix}- {render_scalar(item)}")
    return lines

profile = {
    "me": {
        "name": username,
        "display_name": display_name or username,
        "email": email,
        "account_id": account_id,
        "projects_responsible": discovery["projects_responsible"],
        "default_project": default_project,
        "confluence_workspace": confluence_workspace,
        "confluence_base_url": confluence_base_url,
        "confluence_space_key": confluence_space_key,
        "confluence_parent_id": confluence_parent_id,
        "confluence_space_id": confluence_space_id,
    }
}
profile_path.write_text("\n".join(dump_yaml(profile)) + "\n", encoding="utf-8")

components_yaml = {"components": discovery["components"]}
(project_dir / "components.yaml").write_text("\n".join(dump_yaml(components_yaml)) + "\n", encoding="utf-8")

selected_members = [item for item in discovery["candidate_members"] if item.get("selected")]
team_yaml = {
    "workspace": {
        "name": f"{project_name} Workspace",
        "project": {"key": project_key},
        "ownership": {"components_file": "components.yaml"},
    },
    "team": {
        "members": [
            {
                "name": item["name"],
                "email": item["email"],
                "account_id": item["account_id"],
            }
            for item in selected_members
        ],
        "external_members": [],
        "candidate_members": [
            {
                "name": item["name"],
                "email": item["email"],
                "account_id": item["account_id"],
            }
            for item in discovery["candidate_members"]
        ],
    },
}
(project_dir / "team.yaml").write_text("\n".join(dump_yaml(team_yaml)) + "\n", encoding="utf-8")

(policy_dir / "ticket-schema.json").write_text(
    json.dumps(discovery["ticket_schema"], ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

field_mappings_path = policy_dir.parent / "field-mappings.yaml"
existing = {"defaults": {}, "projects": {}}
if field_mappings_path.is_file():
    def strip_quotes(value: str) -> str:
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value

    def parse_simple_yaml_map(text: str):
        root = {}
        stack = [(-1, root)]
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            match = re.match(r"^(\s*)([^:\n]+):(?:\s*(.*))?$", line)
            if not match:
                continue
            indent = len(match.group(1))
            key = match.group(2).strip()
            raw_value = (match.group(3) or "").strip()
            while len(stack) > 1 and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            if raw_value == "":
                node = {}
                parent[key] = node
                stack.append((indent, node))
            elif raw_value == "{}":
                parent[key] = {}
            else:
                parent[key] = strip_quotes(raw_value)
        return root

    existing = parse_simple_yaml_map(field_mappings_path.read_text(encoding="utf-8"))

defaults = existing.get("defaults") or {}
projects = existing.get("projects") or {}
projects[project_key] = discovery["field_mapping_project"]
field_mappings_path.write_text(
    "\n".join(dump_yaml({"defaults": defaults, "projects": projects})) + "\n",
    encoding="utf-8",
)

epic_list_path = profile_path.parent / "epic-list.yaml"

def parse_recent_epics(text: str):
    lines = text.splitlines()
    epics = []
    in_recent = False
    current = None

    for line in lines:
        if not in_recent:
            if re.match(r"^\s*recent_epics:\s*$", line):
                in_recent = True
            continue
        if in_recent and re.match(r"^\S", line):
            break

        m_key = re.match(r"^\s*-\s*key:\s*([A-Z]+-\d+)\s*$", line)
        if m_key:
            if current:
                epics.append(current)
            current = {"key": m_key.group(1), "title": "", "components": []}
            continue
        if current is None:
            continue

        m_title = re.match(r"^\s*title:\s*(.+?)\s*$", line)
        if m_title:
            current["title"] = m_title.group(1).strip().strip('"').strip("'")
            continue

        m_comps = re.match(r"^\s*components:\s*\[(.*)\]\s*$", line)
        if m_comps:
            raw = m_comps.group(1).strip()
            current["components"] = [
                c.strip().strip('"').strip("'")
                for c in raw.split(",")
                if c.strip()
            ] if raw else []

    if current:
        epics.append(current)
    return epics

existing_recent_epics = []
if epic_list_path.is_file():
    existing_recent_epics = parse_recent_epics(epic_list_path.read_text(encoding="utf-8"))

project_prefix = f"{project_key.upper()}-"
merged_recent_epics = [
    item
    for item in existing_recent_epics
    if not str(item.get("key", "")).startswith(project_prefix)
]
merged_recent_epics.extend(discovery.get("recent_epics") or [])

epic_list_lines = [
    "# Global epic list: conventions and recent epics. Project implied by key prefix (CP-, PAG-).",
    "",
    "epic_management:",
    "  purpose: Manage Story parent linkage through quarterly module epics.",
    "  conventions:",
    '    quarterly_module_epic_naming_pattern: "<Module> Upgrade - <YYQn>"',
    '    story_parent_default_rule: "For functional-module Story, default Parent to module quarterly Epic."',
    '    special_epic_override_rule: "Use a special Epic when user explicitly specifies one or the work is non-quarterly."',
    "",
    "  # JQL template to fetch recent epics (project scope, not Done/Won't Do, last 24w).",
    "  recent_epics_query:",
    '    description: "Project epics, open, created in last 24 weeks"',
    "    jql_template: |",
    "      type = Epic",
    "      AND project = {{project_key}}",
    '      AND status NOT IN (Done, "Won\'t Do")',
    "      AND created >= -24w",
    "      ORDER BY created DESC",
    "    # MCP tool to run this query and refresh recent_epics:",
    "    mcp:",
    "      server: user-mcp-atlassian",
    "      tool: jira_search",
    "      params:",
    '        jql: "jql_template with {{project_key}} replaced by the target project key"',
    '        fields: "key,summary,components"',
    "        limit: 50",
    "",
    "  recent_epics:",
]

if merged_recent_epics:
    epic_list_lines.extend(dump_yaml(merged_recent_epics, 4))

epic_list_path.write_text("\n".join(epic_list_lines) + "\n", encoding="utf-8")
PY

log "Updating .env"
upsert_env CONFLUENCE_EMAIL "$EMAIL"
upsert_env ATLASSIAN_API_TOKEN "$ATLASSIAN_API_TOKEN"
upsert_env ACCOUNT_ID "$ACCOUNT_ID"
upsert_env CONFLUENCE_BASE_URL "$CONFLUENCE_BASE_URL"
upsert_env CONFLUENCE_SPACE_KEY "$CONFLUENCE_SPACE_KEY"
upsert_env CONFLUENCE_PARENT_ID "$CONFLUENCE_PARENT_ID"
upsert_env CONFLUENCE_SPACE_ID "$CONFLUENCE_SPACE_ID"

chmod 600 "$ENV_PATH" || true

log "Initialization completed."
echo "Generated: $PROFILE_PATH"
echo "Updated:   $ENV_PATH"
echo "Generated: $PROJECT_DIR/components.yaml"
echo "Generated: $PROJECT_DIR/team.yaml"
echo "Generated: $POLICY_DIR/ticket-schema.json"
echo "Updated:   $REPO_ROOT/config/policy/field-mappings.yaml"
echo "Updated:   $REPO_ROOT/config/assets/global/epic-list.yaml"
