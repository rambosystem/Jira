from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.common.profile import resolve_profile_path
from scripts.common.ticket_config import (
    load_jira_runtime_profile,
    load_recent_epics,
    load_team_defaults,
)
from scripts.common.ticket_policy import load_issue_field_mapping


POLICY_BUNDLE_PATH = Path("tmp") / "policy.resolved.json"
ISSUE_TYPES = ("Story", "Technical Story")


def _discover_projects(repo_root: Path) -> list[str]:
    project_root = repo_root / "assets" / "project"
    if not project_root.is_dir():
        return []
    keys: list[str] = []
    for child in sorted(project_root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "team.yaml").is_file():
            keys.append(child.name.upper())
    return keys


def _extract_quarter(title: str) -> str:
    m = re.search(r"\b(\d{2}Q[1-4])\b", title.upper())
    return m.group(1) if m else ""


def _build_epic_index(recent_epics: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for epic in recent_epics:
        key = str(epic.get("key", "")).strip().upper()
        if "-" not in key:
            continue
        project = key.split("-", 1)[0]
        title = str(epic.get("title", ""))
        quarter = _extract_quarter(title)
        if not quarter:
            continue
        components = [str(c).strip().lower() for c in (epic.get("components") or []) if str(c).strip()]
        if not components:
            continue
        out.setdefault(project, {}).setdefault(quarter, {})
        for comp in components:
            out[project][quarter].setdefault(comp, key)
    return out


def _source_paths(repo_root: Path, projects: list[str]) -> list[Path]:
    paths = [
        resolve_profile_path(repo_root),
        repo_root / "assets" / "global" / "epic-list.yaml",
        repo_root / "policy" / "field-mappings.yaml",
    ]
    for p in projects:
        paths.append(repo_root / "assets" / "project" / p / "team.yaml")
    # Keep order + dedupe
    seen: set[Path] = set()
    ordered: list[Path] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        ordered.append(p)
    return ordered


def build_policy_bundle(repo_root: Path) -> dict[str, Any]:
    profile = load_jira_runtime_profile(repo_root)
    projects = _discover_projects(repo_root)
    if not projects:
        raise RuntimeError("No projects discovered under assets/project/*/team.yaml")

    team_defaults = {p: load_team_defaults(repo_root, p) for p in projects}
    field_mappings = {
        p: {issue_type: load_issue_field_mapping(repo_root, p, issue_type) for issue_type in ISSUE_TYPES}
        for p in projects
    }
    recent_epics = load_recent_epics(repo_root)
    epic_index = _build_epic_index(recent_epics)

    sources = []
    for p in _source_paths(repo_root, projects):
        if not p.is_file():
            raise RuntimeError(f"Policy source missing: {p}")
        sources.append(
            {
                "path": str(p.relative_to(repo_root)),
                "mtime": int(p.stat().st_mtime),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "default_project": profile["default_project"],
        },
        "projects": projects,
        "team_defaults": team_defaults,
        "field_mappings": field_mappings,
        "recent_epics": recent_epics,
        "epic_index": epic_index,
        "sources": sources,
    }


def write_policy_bundle(repo_root: Path, bundle: dict[str, Any]) -> Path:
    out_path = repo_root / POLICY_BUNDLE_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def load_policy_bundle(repo_root: Path) -> dict[str, Any]:
    path = repo_root / POLICY_BUNDLE_PATH
    if not path.is_file():
        raise RuntimeError(
            f"Policy bundle not found: {path}. Run: python3 scripts/policy/build_policy_json.py"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid policy bundle JSON: {path}. Run: python3 scripts/policy/build_policy_json.py"
        ) from exc

    for src in data.get("sources") or []:
        rel = src.get("path")
        recorded = int(src.get("mtime", 0))
        src_path = repo_root / rel
        if not src_path.is_file():
            raise RuntimeError(
                f"Policy source removed: {src_path}. Rebuild: python3 scripts/policy/build_policy_json.py"
            )
        current = int(src_path.stat().st_mtime)
        if current > recorded:
            raise RuntimeError(
                "Policy bundle is stale. Rebuild: python3 scripts/policy/build_policy_json.py"
            )
    return data
