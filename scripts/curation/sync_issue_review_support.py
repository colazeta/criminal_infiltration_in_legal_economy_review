#!/usr/bin/env python3
"""Synchronise non-decisional reading aids and review guidance into curator issues."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
API = "https://api.github.com"
QUEUE_PATH = ROOT / "data" / "curation" / "review_queue.csv"
AIDS_PATH = ROOT / "data" / "curation" / "reading_aids.json"
READING_HEADING = "## Reading aid — preparatory"
GUIDANCE_HEADING = "## Review guidance — preparatory"


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
            "User-Agent": "criminal-infiltration-review-support-sync",
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


def clean(value: str, limit: int = 2000) -> str:
    return " ".join(str(value or "").split()).replace("`", "'")[:limit]


def inline(value: str, fallback: str = "none") -> str:
    return f"`{clean(value) or fallback}`"


def safe_link(value: str) -> str:
    url = clean(value, 1000)
    if not url.startswith("https://"):
        return "not recorded"
    return f"<{url.replace('<', '%3C').replace('>', '%3E').replace(' ', '%20')}>"


def read_queue(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    ids = [row.get("candidate_id", "") for row in rows]
    if not ids or any(not value for value in ids) or len(ids) != len(set(ids)):
        raise SyncError("review queue candidate IDs are missing or duplicated")
    return rows


def read_aids(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("records"), list):
        raise SyncError("reading aids use an unsupported schema")
    result: dict[str, dict[str, str]] = {}
    for record in payload["records"]:
        candidate_id = str(record.get("candidateId", ""))
        if not candidate_id or candidate_id in result:
            raise SyncError("reading aid candidate IDs are missing or duplicated")
        required = {"kind", "sourceLabel", "sourceUrl", "synopsis", "checkedAt", "note"}
        if any(not clean(record.get(field, "")) for field in required):
            raise SyncError(f"reading aid {candidate_id} is incomplete")
        if not str(record["sourceUrl"]).startswith("https://"):
            raise SyncError(f"reading aid {candidate_id} requires an HTTPS source")
        result[candidate_id] = {key: str(value) for key, value in record.items()}
    return result


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


def replace_section(body: str, heading: str, replacement: str) -> str:
    existing = str(body or "").rstrip()
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}\s*$.*?(?=^##\s|\Z)")
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


def reading_section(aid: dict[str, str]) -> str:
    return f"""{READING_HEADING}

- Aid kind: {inline(aid['kind'])}
- Source: {inline(aid['sourceLabel'])}
- Source URL: {safe_link(aid['sourceUrl'])}
- Review synopsis: {clean(aid['synopsis'], 1500)}
- Last checked: {inline(aid['checkedAt'])}
- Note: {clean(aid['note'], 1000)}

This section is a **non-decisional reading aid**. It stores a short paraphrase and
source locator, never copied abstract/full-text prose. When the source exposes an
actual abstract, the authenticated curator may retrieve and display that text at
review time. A source summary or review synopsis must never be represented as the
author's abstract."""


def focus_for(row: dict[str, str]) -> str:
    for key in ("required_human_action", "legacy_reason", "intake_reason"):
        value = clean(row.get(key, ""), 1000)
        if value:
            return value
    return "Review the available evidence against the current eligibility codebook."


def guidance_for_stage(stage: str) -> tuple[str, str, str]:
    if stage == "metadata_fix":
        return (
            "Identity / metadata gate",
            "none until identity is reliable",
            "Resolve the work/manifestation identity and essential metadata first. Do not make an eligibility decision from an uncertain identifier or title match.",
        )
    if stage == "legacy_rejection_review":
        return (
            "Legacy rejection re-check",
            "title_abstract, escalating to full_text only when genuinely needed",
            "Treat the legacy signal as audit history, not a decision. Rapidly re-apply the current codebook; obvious topic/document mismatches can be closed without reconstructing an infiltration argument that the source does not make.",
        )
    if stage == "manual_review":
        return (
            "Manual scope / boundary gate",
            "title_abstract, then full_text if the boundary remains uncertain",
            "Decide whether the work makes a necessary conceptual, comparative or methodological contribution to criminal infiltration, rather than merely addressing an adjacent organised-crime or AML topic.",
        )
    return (
        "Substantive eligibility gate",
        "title_abstract, then full_text if any core element remains unsupported",
        "Apply the four-part infiltration test. Use maybe_full_text_needed when the abstract cannot support a defensible decision; do not force a binary outcome for convenience.",
    )


def guidance_section(row: dict[str, str]) -> str:
    gate, suggested_stage, instruction = guidance_for_stage(row.get("review_stage", ""))
    focus = focus_for(row)
    assessment = clean(row.get("intake_assessment", "") or row.get("legacy_scope_fit", "")) or "none"
    return f"""{GUIDANCE_HEADING}

- Current gate: {inline(gate)}
- Suggested screening stage: {inline(suggested_stage)}
- Candidate-specific focus: {focus}
- Prior triage signal: {inline(assessment)}

**Four-part core test — all four are required for `eligible_core`:**
1. identifiable criminal actor or interest;
2. a firm, profession, asset, procurement process, market, sector or governance arrangement in the legal economy;
3. sustained access, participation, influence, control or organisational embeddedness;
4. substantive analysis of that relationship, not an incidental mention.

**Decision discipline:**
- `eligible_core` only when the infiltration relationship is central and supported;
- `eligible_contextual` only for an explicit and necessary conceptual, comparative or methodological contribution without direct infiltration evidence;
- `maybe_full_text_needed` when the evidence currently visible is insufficient;
- `not_eligible` when the conceptual boundary is not met, with a controlled exclusion reason;
- `duplicate`, `not_academic` and `not_retrievable` only for those specific conditions;
- if a substantively AML/economic-crime work is `not_eligible`, consider the separate `broader_aml` routing rather than stretching the infiltration definition.

**How to approach this record:** {instruction}

This guidance is preparatory. The prior triage signal, reading aid and mechanical
retrieval/access metadata are **not decisions**. Your submitted curator instruction
remains the scientific decision, and canonical promotion/publication are separate
gates after screening."""


def sync(repository: str, token: str, queue_path: Path, aids_path: Path) -> dict[str, int]:
    queue = read_queue(queue_path)
    aids = read_aids(aids_path)
    queue_ids = {row["candidate_id"] for row in queue}
    unknown_aids = sorted(set(aids) - queue_ids)
    if unknown_aids:
        raise SyncError(f"reading aids refer to unknown candidates: {', '.join(unknown_aids)}")
    issues = issue_inventory(repository, token)
    updated = 0
    missing = 0
    guidance_count = 0
    aid_count = 0
    for row in queue:
        candidate_id = row["candidate_id"]
        issue = issues.get(candidate_id)
        if not issue:
            missing += 1
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            raise SyncError(f"Issue number missing for {candidate_id}")
        current = str(issue.get("body") or "")
        desired = current
        aid = aids.get(candidate_id)
        if aid:
            desired = replace_section(desired, READING_HEADING, reading_section(aid))
            aid_count += 1
        desired = replace_section(desired, GUIDANCE_HEADING, guidance_section(row))
        guidance_count += 1
        if current == desired:
            continue
        api_request(repository, token, "PATCH", f"/issues/{number}", {"body": desired})
        updated += 1
    if missing:
        raise SyncError(f"{missing} queue rows lack a materialised curator issue")
    return {
        "queue": len(queue),
        "guidance": guidance_count,
        "reading_aids": aid_count,
        "updated": updated,
        "missing_issues": missing,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH)
    parser.add_argument("--aids", type=Path, default=AIDS_PATH)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    print(json.dumps(sync(args.repository, token, args.queue, args.aids), sort_keys=True))


if __name__ == "__main__":
    main()
