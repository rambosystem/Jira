from __future__ import annotations

import re
from pathlib import Path

from scripts.common.profile import (
    load_workspace_profile,
    read_profile,
    resolve_profile_path,
)


def load_jira_runtime_profile(repo_root: Path) -> dict[str, str]:
    profile_path = resolve_profile_path(repo_root)
    profile = load_workspace_profile(profile_path)
    out = {
        "base_url": (profile.get("base_url") or "").rstrip("/"),
        "email": profile.get("email") or "",
        "account_id": profile.get("account_id") or "",
        "default_project": profile.get("default_project") or "CP",
        "profile_path": str(profile_path),
    }
    if not out["base_url"]:
        raise RuntimeError(f"Missing confluence_base_url in profile: {profile_path}")
    if not out["email"]:
        raise RuntimeError(f"Missing email in profile: {profile_path}")
    if not out["account_id"]:
        raise RuntimeError(f"Missing account_id in profile: {profile_path}")
    return out


def load_team_defaults(repo_root: Path, project_key: str) -> dict[str, str]:
    path = repo_root / "assets" / "project" / project_key.upper() / "team.yaml"
    text = read_profile(path)

    client_id_match = re.search(
        r"(?m)^\s*client_id:\s*[\"']?([^\"'\n#]+)",
        text,
    )
    assignee_match = re.search(
        r"(?ms)^\s*defaults:\s*\n.*?^\s*assignee:\s*\n.*?^\s*account_id:\s*[\"']?([^\"'\n#]+)",
        text,
    )
    fallback_assignee_match = re.search(
        r"(?m)^\s*default_assignee_account_id:\s*[\"']?([^\"'\n#]+)",
        text,
    )
    return {
        "client_id": (client_id_match.group(1).strip() if client_id_match else "0000"),
        "assignee_account_id": (
            assignee_match.group(1).strip()
            if assignee_match
            else (fallback_assignee_match.group(1).strip() if fallback_assignee_match else "")
        ),
    }


def load_recent_epics(repo_root: Path) -> list[dict[str, object]]:
    path = repo_root / "assets" / "global" / "epic-list.yaml"
    text = read_profile(path)
    lines = text.splitlines()
    in_recent = False
    epics: list[dict[str, object]] = []
    current: dict[str, object] | None = None

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
            if not raw:
                current["components"] = []
            else:
                current["components"] = [c.strip().strip('"').strip("'") for c in raw.split(",") if c.strip()]

    if current:
        epics.append(current)
    return epics
