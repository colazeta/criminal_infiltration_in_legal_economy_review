#!/usr/bin/env python3
"""Synchronise queue-owned candidate metadata into existing curator issues.

This script owns only the primary candidate-record/provenance block and the
single stage label. Mechanical access/abstract/retrieval sections and curator
action comments are deliberately preserved.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from scripts.curation.materialize_queue_issues import (
    GitHubError,
    STAGE_LABEL,
    api_request,
    existing_issues,
    issue_body,
    read_queue,
)


ROOT = Path(__file__).resolve().parents[2]
MECHANICAL_OR_ACTION_HEADER = re.compile(
    r"(?m)^## (?:Access status — mechanical|Abstract coverage — mechanical|Retrieval coverage — mechanical|Curator action)\s*$"
)


def queue_identity_section(repository: str, row: dict[str, str]) -> str:
    """Render the queue-owned prefix without the curator-action section."""

    rendered = issue_body(repository, row)
    marker = "\n## Curator action\n"
    if marker not in rendered:
        raise GitHubError(f"Curator action boundary missing for {row['candidate_id']}")
    return rendered.split(marker, 1)[0].rstrip()


def replace_queue_identity(body: str, repository: str, row: dict[str, str]) -> str:
    """Replace only queue-owned identity/provenance content in an issue body."""

    current = str(body or "").rstrip()
    expected_marker = f"<!-- curator-candidate:{row['candidate_id']} -->"
    if expected_marker not in current:
        raise GitHubError(f"Candidate marker missing for {row['candidate_id']}")
    if not current.startswith(expected_marker):
        raise GitHubError(f"Candidate marker is not the issue prefix for {row['candidate_id']}")

    identity = queue_identity_section(repository, row)
    match = MECHANICAL_OR_ACTION_HEADER.search(current)
    if match:
        suffix = current[match.start() :].lstrip()
        return f"{identity}\n\n{suffix}\n"
    return f"{identity}\n"


def issue_label_names(issue: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for label in issue.get("labels", []):
        if isinstance(label, dict) and label.get("name"):
            names.append(str(label["name"]))
        elif isinstance(label, str) and label:
            names.append(label)
    return names


def desired_labels(issue: dict[str, Any], row: dict[str, str]) -> list[str]:
    stage_label = STAGE_LABEL.get(row.get("review_stage", ""))
    if not stage_label:
        raise GitHubError(f"Unknown review stage for {row.get('candidate_id', 'candidate')}")
    preserved = [name for name in issue_label_names(issue) if not name.startswith("stage:")]
    if "curation:queue" not in preserved:
        preserved.append("curation:queue")
    preserved.append(stage_label)
    # Preserve order while preventing accidental duplicates.
    return list(dict.fromkeys(preserved))


def synchronise(
    repository: str,
    token: str,
    rows: list[dict[str, str]],
    *,
    dry_run: bool = False,
) -> int:
    issues = existing_issues(repository, token)
    writes = 0
    for row in rows:
        candidate_id = row["candidate_id"]
        issue = issues.get(candidate_id)
        if issue is None:
            # Creation remains the responsibility of materialize_queue_issues.py.
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            raise GitHubError(f"GitHub issue number is missing for {candidate_id}")

        current_body = str(issue.get("body") or "")
        new_body = replace_queue_identity(current_body, repository, row)
        current_labels = issue_label_names(issue)
        new_labels = desired_labels(issue, row)
        if current_body == new_body and current_labels == new_labels:
            continue
        writes += 1
        if dry_run:
            continue
        payload: dict[str, object] = {}
        if current_body != new_body:
            payload["body"] = new_body
        if current_labels != new_labels:
            payload["labels"] = new_labels
        api_request(repository, token, "PATCH", f"/issues/{number}", payload)
    return writes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument(
        "--queue",
        type=Path,
        default=ROOT / "data" / "curation" / "review_queue.csv",
    )
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_queue(args.queue)
    token = os.environ.get(args.token_env, "").strip()
    if not token:
        raise GitHubError(f"Missing token in {args.token_env}")
    writes = synchronise(args.repository, token, rows, dry_run=args.dry_run)
    mode = "would update" if args.dry_run else "updated"
    print(f"[OK] {mode} {writes} existing curator candidate issue(s).")


if __name__ == "__main__":
    main()
