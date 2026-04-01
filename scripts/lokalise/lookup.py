"""
Query Lokalise translation keys from CDN (exact match only).

Searches across CDN sources: Common, AmazonSearch.
Local cache: scripts/lokalise/tmp/<Source>_YYYY-MM-DD.js
Uses S3 ETag for conditional download — skips if content unchanged.

Usage:
    python scripts/lokalise/lookup.py "Position" "Sales Manager"
    python scripts/lokalise/lookup.py --json output.json "Position" "Sales Manager"
"""

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

CDN_SOURCES = {
    "Common": "https://pacvue-public-doc.s3.us-west-2.amazonaws.com/lokalise/Common/en.js",
    "AmazonSearch": "https://pacvue-public-doc.s3.us-west-2.amazonaws.com/lokalise/AmazonSearch/en.js",
}

CACHE_DIR = Path(__file__).resolve().parent / "tmp"


def _cache_path(source: str) -> Path:
    return CACHE_DIR / f"{source}_{date.today().isoformat()}.js"


def _etag_path(source: str) -> Path:
    return CACHE_DIR / f".{source}_etag"


def _read_saved_etag(source: str) -> str | None:
    try:
        return _etag_path(source).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def _save_etag(source: str, etag: str):
    _etag_path(source).write_text(etag, encoding="utf-8")


def _download_source(source: str, url: str) -> str:
    """Download or load from cache for a single CDN source."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _cache_path(source)

    if cache.exists():
        print(f"  [{source}] cached: {cache.name}")
        return cache.read_text(encoding="utf-8")

    saved_etag = _read_saved_etag(source)
    req = urllib.request.Request(url)
    if saved_etag:
        req.add_header("If-None-Match", saved_etag)

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            etag = resp.headers.get("ETag", "")
            cache.write_text(raw, encoding="utf-8")
            if etag:
                _save_etag(source, etag)
            print(f"  [{source}] downloaded -> {cache.name}")
            return raw
    except urllib.error.HTTPError as e:
        if e.code == 304:
            cached = sorted(CACHE_DIR.glob(f"{source}_*.js"), reverse=True)
            if cached:
                raw = cached[0].read_text(encoding="utf-8")
                cache.write_text(raw, encoding="utf-8")
                print(f"  [{source}] not modified, reused: {cached[0].name}")
                return raw
        raise


def _parse_js(raw: str) -> dict:
    match = re.search(r"var\s+translations\s*=\s*(\{.*\})\s*;", raw, re.DOTALL)
    if not match:
        return {}
    return json.loads(match.group(1))


def fetch_all() -> dict[str, dict]:
    """Returns {source_name: {key: value, ...}} for each CDN."""
    result = {}
    for source, url in CDN_SOURCES.items():
        try:
            raw = _download_source(source, url)
            result[source] = _parse_js(raw)
        except Exception as exc:
            print(f"  [{source}] ERROR: {exc}", file=sys.stderr)
            result[source] = {}
    return result


def _variants(val: str) -> list[str]:
    """Generate lookup variants: original + numbers replaced with {0}, {1}, ..."""
    variants = [val]
    parts = re.split(r'(\d+)', val)
    if len(parts) > 1:
        idx = 0
        replaced = []
        for p in parts:
            if p.isdigit():
                replaced.append(f"{{{idx}}}")
                idx += 1
            else:
                replaced.append(p)
        variants.append("".join(replaced))
    return variants


def lookup(all_translations: dict[str, dict], values: list[str]):
    """Exact match across all sources; also tries {0}-placeholder variants."""
    results = []
    for val in values:
        found = False
        for candidate in _variants(val):
            candidate_lower = candidate.lower()
            for source, translations in all_translations.items():
                for k, v in translations.items():
                    if v.lower() == candidate_lower:
                        results.append((source, k, v))
                        found = True
        if not found:
            results.append((None, None, val))
    return results


def print_results(results: list[tuple[str | None, str | None, str]]):
    if not results:
        print("No matches found.")
        return

    found = [(s, k, v) for s, k, v in results if s is not None]
    missing = [v for s, k, v in results if s is None]

    if found:
        max_key_len = min(max(len(k) for _, k, _ in found), 50)
        max_src_len = max(len(s) for s, _, _ in found)
        for source, key, val in found:
            display_val = val if len(val) <= 80 else val[:77] + "..."
            print(f"  [{source:<{max_src_len}}]  {key:<{max_key_len}}  =>  {display_val}")

    if missing:
        print(f"\n  NOT FOUND ({len(missing)}):")
        for v in missing:
            display = v if len(v) <= 80 else v[:77] + "..."
            print(f"    - {display}")

    print(f"\nFound: {len(found)}, Missing: {len(missing)}")


def export_json(results: list[tuple[str | None, str | None, str]], path: Path):
    """Export results as JSON grouped by source: { source: { key: value } }."""
    grouped: dict[str, dict[str, str]] = {}
    not_found: list[str] = []

    for source, key, val in results:
        if source is None:
            not_found.append(val)
        else:
            grouped.setdefault(source, {})[key] = val

    output = dict(sorted(grouped.items()))
    if not_found:
        output["_NOT_FOUND"] = not_found

    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for k, v in grouped.items())
    print(f"Exported {total} key:value pairs to {path}")
    if not_found:
        print(f"  ({len(not_found)} not found)")


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(0)

    args = sys.argv[1:]
    json_out = None
    if "--json" in args:
        idx = args.index("--json")
        if idx + 1 < len(args):
            json_out = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("ERROR: --json requires a filename", file=sys.stderr)
            sys.exit(1)

    values = args
    all_trans = fetch_all()
    total = sum(len(t) for t in all_trans.values())
    print(f"Loaded {total} keys from {len(all_trans)} sources.\n")

    results = lookup(all_trans, values)

    if json_out:
        out_path = CACHE_DIR / json_out if not Path(json_out).is_absolute() else Path(json_out)
        export_json(results, out_path)
    else:
        print_results(results)


if __name__ == "__main__":
    main()
