#!/usr/bin/env python3
"""Synchronise assisted abstract-resolution status into curator issues."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from scripts.curation.sync_issue_review_support import (
    SyncError,
    api_request,
    clean,
    inline,
    issue_inventory,
    replace_section,
    safe_link,
)


ROOT = Path(__file__).resolve().parents[2]
RESOLUTION_PATH = ROOT / "data" / "curation" / "residual_abstract_resolution.json"
HEADING = "## Abstract resolution — assisted"
ALLOWED_CLASSES = {
    "full_text_or_intro_ready",
    "publisher_summary_ready",
    "metadata_only",
    "known_noise",
}
ALLOWED_ABSTRACT_STATES = {
    "not_verified_after_targeted_search",
    "not_applicable_noise",
}


def read_resolution(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("records"), list):
        raise SyncError("residual abstract resolution uses an unsupported schema")
    result: dict[str, dict[str, str]] = {}
    required = {
        "resolutionClass",
        "standaloneAbstractStatus",
        "sourceLabel",
        "sourceUrl",
        "checkedAt",
        "nextAction",
        "note",
    }
    for record in payload["records"]:
        candidate_id = clean(record.get("candidateId", ""), 100)
        if not candidate_id or candidate_id in result:
            raise SyncError("residual abstract-resolution candidate IDs are missing or duplicated")
        if any(not clean(record.get(field, "")) for field in required):
            raise SyncError(f"residual abstract-resolution record {candidate_id} is incomplete")
        if record["resolutionClass"] not in ALLOWED_CLASSES:
            raise SyncError(f"unsupported residual resolution class for {candidate_id}")
        if record["standaloneAbstractStatus"] not in ALLOWED_ABSTRACT_STATES:
            raise SyncError(f"unsupported standalone abstract status for {candidate_id}")
        if not str(record["sourceUrl"]).startswith("https://"):
            raise SyncError(f"residual abstract-resolution record {candidate_id} requires HTTPS")
        result[candidate_id] = {key: str(value) for key, value in record.items()}
    return result


def resolution_section(record: dict[str, str]) -> str:
    return f"""{HEADING}

- Resolution class: {inline(record['resolutionClass'])}
- Standalone abstract status: {inline(record['standaloneAbstractStatus'])}
- Best assisted source: {inline(record['sourceLabel'])}
- Source URL: {safe_link(record['sourceUrl'])}
- Last checked: {inline(record['checkedAt'])}
- Next action: {clean(record['nextAction'], 1200)}
- Note: {clean(record['note'], 1200)}

This is an **assisted retrieval disposition**, not a scientific screening decision.
`not_verified_after_targeted_search` means exactly that a standalone abstract was
not verified after the current targeted search; it does **not** assert that no
abstract exists. Review readiness and abstract availability remain separate fields."""


def remove_section(body: str, heading: str) -> str:
    existing = str(body or "").rstrip()
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}\s*$.*?(?=^##\s|\Z)")
    match = pattern.search(existing)
    if not match:
        return f"{existing}\n" if existing else ""
    before = existing[: match.start()].rstrip()
    after = existing[match.end() :].lstrip()
    joined = "\n\n".join(part for part in (before, after) if part)
    return f"{joined}\n" if joined else ""


def sync(repository: str, token: str, resolution_path: Path = RESOLUTION_PATH) -> dict[str, int]:
    records = read_resolution(resolution_path)
    issues = issue_inventory(repository, token)
    missing = sorted(set(records) - set(issues))
    if missing:
        raise SyncError(f"residual abstract-resolution records lack curator issues: {', '.join(missing)}")

    updated = 0
    materialized = 0
    removed = 0
    for candidate_id, issue in issues.items():
        current = str(issue.get("body") or "")
        record = records.get(candidate_id)
        if record:
            desired = replace_section(current, HEADING, resolution_section(record))
            materialized += 1
        else:
            desired = remove_section(current, HEADING)
            if current != desired and HEADING in current:
                removed += 1
        if current == desired:
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            raise SyncError(f"Issue number missing for {candidate_id}")
        api_request(repository, token, "PATCH", f"/issues/{number}", {"body": desired})
        updated += 1

    return {
        "registered": len(records),
        "materialized": materialized,
        "removed": removed,
        "updated": updated,
        "missing_issues": len(missing),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--resolution", type=Path, default=RESOLUTION_PATH)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    print(json.dumps(sync(args.repository, token, args.resolution), sort_keys=True))


if __name__ == "__main__":
    main()
