#!/usr/bin/env python3
"""Synchronise mechanical retrieval coverage into materialised curator issues."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
API = "https://api.github.com"
COVERAGE_PATH = ROOT / "data" / "curation" / "retrieval_coverage.csv"
SECTION_HEADING = "## Retrieval coverage — mechanical"


class SyncError(RuntimeError):
    pass


def api_request(repository: str, token: str, method: str, path: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{API}/repos/{repository}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "criminal-infiltration-retrieval-sync",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise SyncError(f"GitHub API {method} {path} failed ({exc.code}): {detail}") from exc


def paginated(repository: str, token: str, path: str):
    rows = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        payload = api_request(repository, token, "GET", f"{path}{separator}per_page=100&page={page}")
        if not isinstance(payload, list):
            raise SyncError(f"GitHub API returned non-list for {path}")
        rows.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            return rows
        page += 1


def safe_link(value: str) -> str:
    value = " ".join((value or "").split())
    if not value:
        return "not resolved"
    return f"<{value.replace('<', '%3C').replace('>', '%3E').replace(' ', '%20')}>"


def inline(value: str, fallback: str = "none") -> str:
    clean = " ".join((value or "").split()).replace("`", "'")
    return f"`{clean or fallback}`"


def section(row: dict[str, str]) -> str:
    return f"""{SECTION_HEADING}

- Resolution status: {inline(row.get('resolution_status', ''))}
- Best URL: {safe_link(row.get('best_url', ''))}
- Best URL kind: {inline(row.get('best_url_kind', ''))}
- Direct full text: {safe_link(row.get('full_text_url', ''))}
- Open-access location: {safe_link(row.get('open_access_url', ''))}
- Landing page: {safe_link(row.get('landing_url', ''))}
- DOI URL: {safe_link(row.get('doi_url', ''))}
- Resolver sources: {inline(row.get('resolution_sources', ''))}
- Match method: {inline(row.get('match_method', ''))}
- Match confidence: {inline(row.get('match_confidence', ''))}
- Last checked: {inline(row.get('checked_at', ''))}

This is mechanical retrieval metadata only. It does not establish eligibility,
quality, identity beyond the recorded match confidence, or publication status."""


def replace_section(body: str, replacement: str) -> str:
    existing = str(body or "").rstrip()
    pattern = re.compile(r"(?ms)^## Retrieval coverage — mechanical\s*$.*?(?=^##\s|\Z)")
    match = pattern.search(existing)
    if match:
        before = existing[: match.start()].rstrip()
        after = existing[match.end() :].lstrip()
        return "\n\n".join(part for part in (before, replacement, after) if part) + "\n"

    action = re.search(r"(?m)^## Curator action\s*$", existing)
    if action:
        before = existing[: action.start()].rstrip()
        after = existing[action.start() :].lstrip()
        return f"{before}\n\n{replacement}\n\n{after}\n"
    return f"{existing}\n\n{replacement}\n" if existing else f"{replacement}\n"


def read_coverage(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def issue_inventory(repository: str, token: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for issue in paginated(repository, token, "/issues?state=all"):
        if "pull_request" in issue:
            continue
        body = str(issue.get("body") or "")
        match = re.search(r"<!--\s*curator-candidate:([A-Z0-9-]+)\s*-->", body)
        if not match:
            continue
        candidate_id = match.group(1)
        if candidate_id in result:
            raise SyncError(f"Multiple issues represent {candidate_id}")
        result[candidate_id] = issue
    return result


def sync(repository: str, token: str, coverage_path: Path) -> dict[str, int]:
    rows = read_coverage(coverage_path)
    if not rows:
        print("Retrieval coverage is not materialised yet; nothing to sync.")
        return {"coverage": 0, "updated": 0, "missing_issues": 0}
    issues = issue_inventory(repository, token)
    updated = 0
    missing = 0
    for row in rows:
        candidate_id = row.get("candidate_id", "")
        issue = issues.get(candidate_id)
        if not issue:
            missing += 1
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            raise SyncError(f"Issue number missing for {candidate_id}")
        current = str(issue.get("body") or "")
        desired = replace_section(current, section(row))
        if current == desired:
            continue
        api_request(repository, token, "PATCH", f"/issues/{number}", {"body": desired})
        updated += 1
    if missing:
        raise SyncError(f"{missing} retrieval rows lack a materialised curator issue")
    return {"coverage": len(rows), "updated": updated, "missing_issues": missing}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    result = sync(args.repository, token, args.coverage)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
