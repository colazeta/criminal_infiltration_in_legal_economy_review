#!/usr/bin/env python3
"""Detect a missing daily surveillance ledger entry without fabricating a run."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROME = ZoneInfo("Europe/Rome")
API_ROOT = "https://api.github.com"
INCIDENT_TITLE = "[OPS] Daily surveillance heartbeat missing"
INCIDENT_MARKER = "<!-- surveillance-heartbeat-incident:v1 -->"
SURVEILLANCE_MARKER = "<!-- surveillance-run:v1 -->"


def batch_id_for(day: date) -> str:
    return f"ACADEMIC-{day.isoformat()}"


def rome_today(now: datetime | None = None) -> date:
    moment = now or datetime.now(tz=ROME)
    if moment.tzinfo is None:
        raise ValueError("heartbeat clock must be timezone-aware")
    return moment.astimezone(ROME).date()


def comment_has_batch(body: str, batch_id: str) -> bool:
    """Require the governed marker and an exact JSON batch-id field."""

    text = str(body or "")
    if SURVEILLANCE_MARKER not in text:
        return False
    pattern = rf'"batch_id"\s*:\s*"{re.escape(batch_id)}"'
    return re.search(pattern, text) is not None


def incident_body(batch_id: str, checked_at: datetime) -> str:
    checked = checked_at.astimezone(ROME).isoformat(timespec="seconds")
    return "\n".join(
        [
            INCIDENT_MARKER,
            "",
            "The repository watchdog did not find the governed daily surveillance ledger entry for",
            f"`{batch_id}` by the scheduled heartbeat check.",
            "",
            "**Interpretation:** this is an operational absence only. It is **not** a zero-result",
            "search, **not** a failed source, and **not** evidence for scientific saturation.",
            "",
            "Expected recovery: run the external `Daily AML & CI Research` task and materialise the",
            "governed `completed`, `partial`, or `failed` ledger comment. Do not invent or backfill a",
            "run unless its exact search window, source outcomes, counts, and provenance can be",
            "reproduced and validated under the current contract.",
            "",
            f"Last watchdog check (Europe/Rome): `{checked}`.",
        ]
    )


def api_request(
    path: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "cile-surveillance-heartbeat",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(f"{API_ROOT}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed GitHub API root
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {path}: {detail[:500]}") from exc
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def paginated(repository: str, resource: str, token: str, **params: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for page in range(1, 101):
        query = urlencode({**params, "per_page": "100", "page": str(page)})
        payload = api_request(f"/repos/{repository}/{resource}?{query}", token)
        if not isinstance(payload, list):
            raise RuntimeError(f"GitHub returned a non-list payload for {resource}")
        rows.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            break
    else:
        raise RuntimeError(f"pagination limit exceeded for {resource}")
    return rows


def ledger_has_batch(repository: str, ledger_issue: int, token: str, batch_id: str) -> bool:
    comments = paginated(repository, f"issues/{ledger_issue}/comments", token)
    return any(comment_has_batch(str(comment.get("body", "")), batch_id) for comment in comments)


def find_open_incident(repository: str, token: str) -> dict[str, Any] | None:
    issues = paginated(repository, "issues", token, state="open", sort="created", direction="desc")
    for issue in issues:
        if issue.get("pull_request"):
            continue
        if issue.get("title") != INCIDENT_TITLE:
            continue
        if INCIDENT_MARKER not in str(issue.get("body", "")):
            continue
        return issue
    return None


def reconcile(repository: str, ledger_issue: int, token: str, day: date, *, dry_run: bool = False) -> str:
    batch_id = batch_id_for(day)
    present = ledger_has_batch(repository, ledger_issue, token, batch_id)
    incident = find_open_incident(repository, token)

    if present:
        if incident is None:
            return f"ok:{batch_id}"
        if not dry_run:
            api_request(
                f"/repos/{repository}/issues/{int(incident['number'])}",
                token,
                method="PATCH",
                payload={"state": "closed"},
            )
        return f"recovered:{batch_id}"

    body = incident_body(batch_id, datetime.now(tz=ROME))
    if incident is None:
        if not dry_run:
            api_request(
                f"/repos/{repository}/issues",
                token,
                method="POST",
                payload={"title": INCIDENT_TITLE, "body": body},
            )
        return f"opened:{batch_id}"

    if not dry_run:
        api_request(
            f"/repos/{repository}/issues/{int(incident['number'])}",
            token,
            method="PATCH",
            payload={"body": body},
        )
    return f"updated:{batch_id}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ledger-issue", type=int, default=30)
    parser.add_argument("--date", help="Override Europe/Rome date (YYYY-MM-DD) for deterministic checks")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        raise SystemExit("invalid repository")
    if args.ledger_issue < 1:
        raise SystemExit("invalid ledger issue")

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    day = date.fromisoformat(args.date) if args.date else rome_today()
    print(reconcile(args.repository, args.ledger_issue, token, day, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
