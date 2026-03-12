#!/usr/bin/env python3
"""
Generate Request PIN Report ADF JSON from Jira PIN issues with concurrent LLM analysis.

Flow:
1) Resolve PIN IDs (explicit list or latest N assigned PIN requests).
2) Fetch all issue details in one Jira API call (`key in (...)`).
3) Analyze each issue description concurrently via LLM.
4) Build one merged ADF doc JSON for Confluence create-page.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common.atlassian import basic_auth, jira_api_v3_url
from scripts.common.env import load_dotenv
from scripts.common.http import request_json
from scripts.common.profile import load_atlassian_profile, resolve_profile_path

PROFILE_PATH = resolve_profile_path(REPO_ROOT)
ENV_PATH = REPO_ROOT / ".env"

DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/"
DEFAULT_STATUSES = ("Backlog", "Ready for Technical Review")
DEFAULT_FIELDS = ("key", "summary", "status", "priority", "created", "description")

def load_profile() -> dict[str, str]:
    profile = load_atlassian_profile(PROFILE_PATH)
    account_id = profile["account_id"]
    email = profile["email"]
    confluence_base_url = profile["base_url"]
    jira_base_url = confluence_base_url or ""
    if not jira_base_url:
        raise RuntimeError("Cannot resolve Jira base URL from profile (confluence_base_url).")
    if not account_id:
        raise RuntimeError("Cannot resolve me.account_id from profile.")
    return {
        "account_id": account_id,
        "email": email,
        "jira_base_url": jira_base_url.rstrip("/"),
    }


def jira_request(base_url: str, auth: str, jql: str, fields: list[str], limit: int = 100) -> dict[str, Any]:
    # Use /rest/api/3/search/jql (old /rest/api/3/search returns 410 Gone)
    url = jira_api_v3_url(base_url, "/search/jql")
    payload = {"jql": jql, "maxResults": limit, "fields": list(fields)}
    return request_json(
        url,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        data=payload,
        insecure_env_var="PIN_REPORT_INSECURE_SSL",
    )


def parse_pin_ids(raw: str) -> list[str]:
    if not raw.strip():
        return []
    ids = []
    for item in re.split(r"[,\s]+", raw.strip()):
        if not item:
            continue
        pin = item.upper()
        if not re.fullmatch(r"PIN-\d+", pin):
            continue
        ids.append(pin)
    # keep order, dedupe
    seen = set()
    ordered = []
    for pin in ids:
        if pin in seen:
            continue
        seen.add(pin)
        ordered.append(pin)
    return ordered


def resolve_pin_ids(args: argparse.Namespace, profile: dict[str, str], auth: str) -> list[str]:
    explicit = parse_pin_ids(args.pin_ids)
    if explicit:
        return explicit

    n = args.latest
    if n <= 0:
        return []
    statuses = ", ".join(f'"{s}"' for s in DEFAULT_STATUSES)
    jql = (
        "project = PIN "
        f'AND assignee in ("{profile["account_id"]}") '
        f"AND status IN ({statuses}) "
        "ORDER BY created DESC"
    )
    data = jira_request(profile["jira_base_url"], auth, jql, ["key"], limit=n)
    issues = data.get("issues") or []
    return [i.get("key", "").upper() for i in issues if i.get("key")]


def openai_chat_completion(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    data = request_json(
        url,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        data=payload,
        insecure_env_var="PIN_REPORT_INSECURE_SSL",
    )
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM response has no choices.")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("LLM response has empty content.")
    return content


def normalize_json(text: str) -> dict[str, str]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid LLM JSON: {exc}") from exc
    fields = {}
    for key in ("problem", "background", "impact", "expectation"):
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            fields[key] = "暂无描述"
        else:
            fields[key] = value.strip()
    return fields


def adf_text(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def adf_paragraph(parts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "paragraph", "content": parts}


def adf_empty_paragraph() -> dict[str, Any]:
    """Empty paragraph for vertical spacing between PIN blocks."""
    return {"type": "paragraph", "content": []}


def adf_bullet_item(label: str, value: str) -> dict[str, Any]:
    return {
        "type": "listItem",
        "content": [
            adf_paragraph(
                [
                    {"type": "text", "text": f"{label}：", "marks": [{"type": "strong"}]},
                    adf_text(value),
                ]
            )
        ],
    }


def build_pin_block(issue_key: str, base_url: str, digest: dict[str, str]) -> list[dict[str, Any]]:
    browse_url = f"{base_url}/browse/{issue_key}"
    return [
        {"type": "blockCard", "attrs": {"url": browse_url}},
        {"type": "heading", "attrs": {"level": 3}, "content": [adf_text("需求要点")]},
        {
            "type": "bulletList",
            "content": [
                adf_bullet_item("问题", digest["problem"]),
                adf_bullet_item("背景", digest["background"]),
                adf_bullet_item("业务影响", digest["impact"]),
                adf_bullet_item("期望", digest["expectation"]),
            ],
        },
    ]


def run() -> int:
    load_dotenv(ENV_PATH)
    parser = argparse.ArgumentParser(description="Generate Request PIN Report ADF JSON via concurrent LLM analysis.")
    parser.add_argument("--pin-ids", default="", help="Comma/space separated PIN IDs, e.g. 'PIN-1,PIN-2'")
    parser.add_argument("--latest", type=int, default=0, help="If --pin-ids empty, fetch latest N unprocessed PIN requests")
    parser.add_argument("--model", default=os.environ.get("PIN_REPORT_LLM_MODEL", DEFAULT_LLM_MODEL))
    parser.add_argument("--llm-base-url", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_LLM_BASE_URL))
    parser.add_argument("--concurrency", type=int, default=5, help="LLM concurrent workers")
    parser.add_argument("--output", default="", help="Write final ADF JSON to file (optional)")
    parser.add_argument("--analysis-output", default="", help="Write per-PIN analysis JSON to file (optional)")
    parser.add_argument("--from-analysis", default="", help="Build ADF from existing pin_analysis.json (no Jira/LLM)")
    args = parser.parse_args()

    try:
        profile = load_profile()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.from_analysis:
        # Build ADF from existing analysis file only (no Jira, no LLM)
        analysis_path = Path(args.from_analysis)
        if not analysis_path.is_absolute():
            analysis_path = REPO_ROOT / "tmp" / analysis_path
        if not analysis_path.is_file():
            print(f"Error: analysis file not found: {analysis_path}", file=sys.stderr)
            return 1
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        ordered_keys = list(data.get("pin_ids") or [])
        raw_analyses = data.get("analyses") or {}
        analyses = {}
        for key in ordered_keys:
            a = raw_analyses.get(key) or {}
            analyses[key] = {
                "problem": (a.get("problem") or "").strip() or "暂无描述",
                "background": (a.get("background") or "").strip() or "暂无描述",
                "impact": (a.get("impact") or "").strip() or "暂无描述",
                "expectation": (a.get("expectation") or "").strip() or "暂无描述",
            }
        if not ordered_keys:
            print("Error: no pin_ids in analysis file.", file=sys.stderr)
            return 1
        content = []
        for i, key in enumerate(ordered_keys):
            content.extend(build_pin_block(key, profile["jira_base_url"], analyses[key]))
            if i < len(ordered_keys) - 1:
                content.append(adf_empty_paragraph())
        adf_doc = {"version": 1, "type": "doc", "content": content}
        output_text = json.dumps(adf_doc, ensure_ascii=False)
        if args.output:
            output_path = Path(args.output)
            if not output_path.is_absolute():
                output_path = REPO_ROOT / "tmp" / output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_text, encoding="utf-8")
            print(f"Wrote ADF to {output_path}", file=sys.stderr)
        else:
            print(output_text)
        return 0

    api_key = os.environ.get("DEEPSEEK_KEY")
    if not api_key:
        print("Error: DEEPSEEK_KEY is required (set in .env or environment).", file=sys.stderr)
        return 1
    token = os.environ.get("ATLASSIAN_API_TOKEN")
    if not token:
        print("Error: ATLASSIAN_API_TOKEN is required.", file=sys.stderr)
        return 1
    if not profile.get("email"):
        print("Error: profile email is required for Jira auth.", file=sys.stderr)
        return 1

    jira_auth = basic_auth(profile["email"], token)
    try:
        pin_ids = resolve_pin_ids(args, profile, jira_auth)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: Jira request failed ({exc.code}). Response: {detail}", file=sys.stderr)
        return 1
    if not pin_ids:
        print("Error: no PIN IDs resolved. Provide --pin-ids or --latest N (>0).", file=sys.stderr)
        return 1

    in_clause = ",".join(f'"{k}"' for k in pin_ids)
    fetch_jql = f"project = PIN AND key IN ({in_clause}) ORDER BY created DESC"
    try:
        search_data = jira_request(profile["jira_base_url"], jira_auth, fetch_jql, list(DEFAULT_FIELDS), limit=len(pin_ids))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: Jira request failed ({exc.code}). {detail}", file=sys.stderr)
        return 1

    issue_map: dict[str, dict[str, Any]] = {}
    for issue in search_data.get("issues") or []:
        key = str(issue.get("key") or "").upper()
        if key:
            issue_map[key] = issue

    missing = [k for k in pin_ids if k not in issue_map]
    if missing:
        print(f"Warning: missing or inaccessible issues: {', '.join(missing)}", file=sys.stderr)

    ordered_keys = [k for k in pin_ids if k in issue_map]
    if not ordered_keys:
        print("Error: no accessible PIN issues found.", file=sys.stderr)
        return 1

    system_prompt = (
        "你是产品需求分析助手。"
        "请基于 Jira issue 的 description 提炼四项字段，并只输出 JSON 对象："
        '{"problem":"...","background":"...","impact":"...","expectation":"..."}。'
        "字段内容用中文，简洁准确，不杜撰。缺失信息填写“暂无描述”。"
    )

    analyses: dict[str, dict[str, str]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = {}
        for key in ordered_keys:
            issue = issue_map[key]
            fields = issue.get("fields") or {}
            description = fields.get("description")
            summary = fields.get("summary") or ""
            payload = {
                "key": key,
                "summary": summary,
                "description": description,
            }
            user_prompt = "请分析以下 Jira issue，并输出指定 JSON：\n" + json.dumps(payload, ensure_ascii=False)
            fut = pool.submit(
                openai_chat_completion,
                api_key,
                args.llm_base_url,
                args.model,
                system_prompt,
                user_prompt,
            )
            futures[fut] = key

        for fut in as_completed(futures):
            key = futures[fut]
            try:
                analyses[key] = normalize_json(fut.result())
            except Exception as exc:
                print(f"Warning: LLM analysis failed for {key}: {exc}", file=sys.stderr)
                analyses[key] = {
                    "problem": "暂无描述",
                    "background": "暂无描述",
                    "impact": "暂无描述",
                    "expectation": "暂无描述",
                }

    content: list[dict[str, Any]] = []
    for i, key in enumerate(ordered_keys):
        content.extend(build_pin_block(key, profile["jira_base_url"], analyses[key]))
        if i < len(ordered_keys) - 1:
            content.append(adf_empty_paragraph())

    adf_doc = {"version": 1, "type": "doc", "content": content}

    if args.analysis_output:
        analysis_path = Path(args.analysis_output)
        if not analysis_path.is_absolute():
            analysis_path = REPO_ROOT / "tmp" / analysis_path
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_path.write_text(
            json.dumps(
                {"pin_ids": ordered_keys, "missing": missing, "analyses": analyses},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    output_text = json.dumps(adf_doc, ensure_ascii=False)
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = REPO_ROOT / "tmp" / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(run())
