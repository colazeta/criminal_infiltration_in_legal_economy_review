#!/usr/bin/env python3
"""Create one idempotent GitHub review issue per materialised candidate.

The script never changes screening or publication state. It exposes only the
existing bibliographic metadata and clearly labels pilot or daily-intake
signals as non-authoritative provenance.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
API = "https://api.github.com"
LABELS = {
    "curation:queue": ("49665c", "Materialised candidate awaiting curator review"),
    "curation:decision": ("9b472f", "Explicit owner-curator decision request"),
    "stage:metadata-fix": ("d4a72c", "Bibliographic metadata requires repair"),
    "stage:manual-review": ("7a6f9b", "Manual scope or contextual review"),
    "stage:abstract-review": ("2b6f8a", "Abstract or full-text review required"),
    "stage:legacy-rejection-review": (
        "8b8b83",
        "Pilot rejection signal retained for human re-checking",
    ),
}
STAGE_LABEL = {
    "metadata_fix": "stage:metadata-fix",
    "manual_review": "stage:manual-review",
    "abstract_full_text_review": "stage:abstract-review",
    "legacy_rejection_review": "stage:legacy-rejection-review",
}
STAGE_NAME = {
    "metadata_fix": "Metadata repair",
    "manual_review": "Manual scope review",
    "abstract_full_text_review": "Abstract / full-text review",
    "legacy_rejection_review": "Legacy rejection re-check",
}
ACTIVE_STATUSES = {"pending", "needs_full_text"}
QUEUE_STATUSES = ACTIVE_STATUSES | {
    "screened_eligible_core",
    "screened_eligible_contextual",
    "screened_not_eligible",
    "duplicate_confirmed",
    "screened_not_academic",
    "screened_not_retrievable",
}


class GitHubError(RuntimeError):
    """Raised when the GitHub issue inventory cannot be materialised safely."""


def read_queue(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    candidate_ids = {row.get("candidate_id", "") for row in rows}
    if (
        len(rows) < 55
        or "" in candidate_ids
        or len(candidate_ids) != len(rows)
    ):
        raise GitHubError("Expected at least 55 unique candidates in the curator queue")
    return rows


def read_actions(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise GitHubError("Curator actions file has no header")
        return [dict(row) for row in reader]


def api_request(
    repository: str,
    token: str,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> object:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{API}/repos/{repository}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "criminal-infiltration-curator-queue",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise GitHubError(
            f"GitHub API {method} {path} failed ({exc.code}): {detail}"
        ) from exc


def paginated(
    repository: str, token: str, path: str
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        payload = api_request(
            repository,
            token,
            "GET",
            f"{path}{separator}per_page=100&page={page}",
        )
        if not isinstance(payload, list):
            raise GitHubError(f"GitHub API returned a non-list for {path}")
        rows.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            return rows
        page += 1


def issue_title(row: dict[str, str]) -> str:
    title = " ".join(row["title"].split()) or "Untitled candidate"
    if len(title) > 90:
        title = title[:87].rstrip() + "…"
    return f"[CURATION] {row['candidate_id']} — {title}"


def decision_form_url(repository: str, candidate_id: str) -> str:
    query = urlencode(
        {
            "template": "candidate_decision.yml",
            "title": f"[CURATOR] {candidate_id}",
        }
    )
    return f"https://github.com/{repository}/issues/new?{query}"


def markdown_text(value: str, fallback: str = "Not recorded") -> str:
    value = " ".join((value or "").split())
    return value.replace("|", "\\|") if value else fallback


def inline_code(value: str, fallback: str = "none") -> str:
    value = " ".join((value or "").split()).replace("`", "'")
    return f"`{value or fallback}`"


def source_links(value: str) -> str:
    links = [link.strip() for link in (value or "").split("; ") if link.strip()]
    if not links:
        return "- Source links: not recorded"
    rendered = []
    for index, link in enumerate(links, start=1):
        safe_link = link.replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")
        rendered.append(f"- Source link {index}: <{safe_link}>")
    return "\n".join(rendered)


def issue_body(repository: str, row: dict[str, str]) -> str:
    doi = row["doi"] or "Not recorded"
    if row["doi"]:
        doi = f"[{row['doi']}](https://doi.org/{quote(row['doi'], safe='/.:()')})"
    stage_name = STAGE_NAME.get(row["review_stage"])
    if not stage_name:
        raise GitHubError(f"Unknown review stage for {row['candidate_id']}")
    if row.get("origin") == "daily_surveillance":
        provenance = f"""## Daily intake provenance — not a decision

- Intake assessment: {inline_code(row.get('intake_assessment', ''))}
- Verification status: {inline_code(row.get('verification_status', ''))}
- Possible duplicate note: {markdown_text(row.get('possible_duplicate', ''), 'none')}
- Metadata conflict: {markdown_text(row.get('metadata_conflict', ''), 'none')}
- Intake reason: {markdown_text(row.get('intake_reason', ''), 'not recorded')}
- Required human action: {markdown_text(row.get('required_human_action', ''), 'not recorded')}
- Query IDs: {inline_code(row.get('source_query_id', ''))}
{source_links(row.get('source_links', ''))}
- Provenance: {inline_code(row.get('provenance', ''))}

The intake assessment and verification label above are retained only for
triage and audit. They are not a governed eligibility decision, exclusion,
duplicate confirmation or publication approval. Review the available evidence
under the current four-part test."""
    elif row.get("origin", "").startswith("legacy_"):
        provenance = f"""## Pilot provenance — not a decision

- Legacy signal: {inline_code(row.get('legacy_recommendation', ''))}
- Legacy scope label: {inline_code(row.get('legacy_scope_fit', ''))}
- Pilot note: {markdown_text(row.get('legacy_reason', ''), 'No additional pilot note.')}
- Provenance: {inline_code(row.get('provenance', ''))}

The legacy signal above is retained only for audit. It is not a governed
eligibility decision, exclusion, duplicate confirmation or publication
approval. Review the available evidence under the current four-part test."""
    else:
        raise GitHubError(
            f"Unknown queue origin for {row.get('candidate_id', 'candidate')}"
        )
    return f"""<!-- curator-candidate:{row['candidate_id']} -->

## Candidate record

| Field | Value |
|---|---|
| Candidate ID | `{row['candidate_id']}` |
| Title | {markdown_text(row['title'])} |
| Authors | {markdown_text(row['authors'])} |
| Year | {markdown_text(row['year'])} |
| Venue | {markdown_text(row['venue'])} |
| DOI | {doi} |
| Source | {markdown_text(row['source'], 'Not recorded')} |
| Current review stage | **{stage_name}** |

{provenance}

## Curator action

[Record an evidence-backed decision]({decision_form_url(repository, row['candidate_id'])})

Copy the candidate ID exactly into the authenticated decision form. The form
prepares a reviewable pull request; it cannot publish the work or merge its own
change.
"""


def ensure_labels(repository: str, token: str) -> None:
    existing = {
        str(row.get("name"))
        for row in paginated(repository, token, "/labels")
        if row.get("name")
    }
    for name, (colour, description) in LABELS.items():
        if name in existing:
            continue
        api_request(
            repository,
            token,
            "POST",
            "/labels",
            {"name": name, "color": colour, "description": description},
        )


def existing_issues(
    repository: str, token: str
) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for issue in paginated(repository, token, "/issues?state=all"):
        if "pull_request" in issue:
            continue
        body = str(issue.get("body") or "")
        for candidate_id in set(
            part.split(" -->", 1)[0]
            for part in body.split("<!-- curator-candidate:")[1:]
            if " -->" in part
        ):
            candidate_id = candidate_id.strip()
            if candidate_id in records:
                raise GitHubError(
                    f"Multiple GitHub issues represent candidate {candidate_id}"
                )
            records[candidate_id] = issue
    return records


def actions_by_id(actions: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for action in actions:
        action_id = action.get("action_id", "")
        if not action_id or action_id in result:
            raise GitHubError("Curator actions contain an empty or duplicate action ID")
        result[action_id] = action
    return result


def validate_action_links(
    rows: list[dict[str, str]], actions: dict[str, dict[str, str]]
) -> None:
    for row in rows:
        action_id = row.get("last_action_id", "")
        status = row.get("current_status", "")
        if status not in QUEUE_STATUSES:
            raise GitHubError(
                f"Candidate {row.get('candidate_id')} has an invalid queue status"
            )
        if status == "pending" and not action_id:
            continue
        action = actions.get(action_id)
        if not action or action.get("candidate_id") != row.get("candidate_id"):
            raise GitHubError(
                f"Candidate {row.get('candidate_id')} lacks its current curator action"
            )


def action_comment(row: dict[str, str], action: dict[str, str]) -> str:
    action_id = action["action_id"]
    issue_number = action["github_issue_number"]
    return f"""<!-- curator-action:{action_id} -->
## Queue state updated

- Current status: {inline_code(row['current_status'])}
- Recorded decision: {inline_code(action['decision'])}
- Append-only action: {inline_code(action_id)}
- Decision instruction: #{issue_number}

This updates the curator queue only. It does not assign a canonical paper ID or
approve publication.
"""


def reconcile_issue(
    repository: str,
    token: str,
    row: dict[str, str],
    issue: dict[str, object],
    actions: dict[str, dict[str, str]],
) -> int:
    number = issue.get("number")
    if not isinstance(number, int):
        raise GitHubError(f"GitHub issue number is missing for {row['candidate_id']}")
    writes = 0
    action_id = row.get("last_action_id", "")
    if action_id:
        marker = f"<!-- curator-action:{action_id} -->"
        comments = paginated(repository, token, f"/issues/{number}/comments")
        if not any(marker in str(comment.get("body") or "") for comment in comments):
            api_request(
                repository,
                token,
                "POST",
                f"/issues/{number}/comments",
                {"body": action_comment(row, actions[action_id])},
            )
            writes += 1
    desired_state = "open" if row["current_status"] in ACTIVE_STATUSES else "closed"
    if issue.get("state") != desired_state:
        payload: dict[str, object] = {"state": desired_state}
        if desired_state == "closed":
            payload["state_reason"] = "completed"
        api_request(repository, token, "PATCH", f"/issues/{number}", payload)
        writes += 1
    labels = {
        str(label.get("name"))
        for label in issue.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    }
    if (
        row["current_status"] == "needs_full_text"
        and "stage:abstract-review" not in labels
    ):
        api_request(
            repository,
            token,
            "POST",
            f"/issues/{number}/labels",
            {"labels": ["stage:abstract-review"]},
        )
        writes += 1
    return writes


def materialise(
    repository: str,
    token: str,
    rows: list[dict[str, str]],
    actions: list[dict[str, str]],
) -> tuple[int, int]:
    ensure_labels(repository, token)
    action_index = actions_by_id(actions)
    validate_action_links(rows, action_index)
    existing = existing_issues(repository, token)
    created = 0
    reconciled = 0
    for row in rows:
        candidate_id = row["candidate_id"]
        issue = existing.get(candidate_id)
        if issue is None:
            stage_label = STAGE_LABEL.get(row["review_stage"])
            if not stage_label:
                raise GitHubError(f"Unknown review stage for {candidate_id}")
            response = api_request(
                repository,
                token,
                "POST",
                "/issues",
                {
                    "title": issue_title(row),
                    "body": issue_body(repository, row),
                    "labels": ["curation:queue", stage_label],
                },
            )
            if not isinstance(response, dict):
                raise GitHubError(f"GitHub did not return issue data for {candidate_id}")
            issue = response
            created += 1
            time.sleep(0.1)
        reconciled += reconcile_issue(
            repository, token, row, issue, action_index
        )
    return created, reconciled


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument(
        "--queue",
        type=Path,
        default=ROOT / "data" / "curation" / "review_queue.csv",
    )
    parser.add_argument(
        "--actions",
        type=Path,
        default=ROOT / "data" / "curation" / "actions.csv",
    )
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_queue(args.queue)
    actions = read_actions(args.actions)
    action_index = actions_by_id(actions)
    validate_action_links(rows, action_index)
    if args.dry_run:
        for row in rows:
            issue_body(args.repository, row)
        print(f"[OK] Validated {len(rows)} curator issue payloads without writing.")
        return
    token = os.environ.get(args.token_env, "").strip()
    if not token:
        raise GitHubError(f"Missing token in {args.token_env}")
    created, reconciled = materialise(args.repository, token, rows, actions)
    print(
        f"[OK] Created {created} curator issue(s) and applied "
        f"{reconciled} idempotent state update(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, json.JSONDecodeError, GitHubError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
