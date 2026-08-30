#!/usr/bin/env python3
"""Fetch and validate aggregate surveillance comments from a GitHub issue."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from surveillance import REPOSITORY_FULL_NAME, MetricsError, validate_run


MARKER = "<!-- surveillance-run:v1 -->"
JSON_BLOCK = re.compile(
    re.escape(MARKER) + r"\s*```json\s*(\{.*?\})\s*```",
    re.DOTALL,
)
INTAKE_TITLE_PREFIX = "[INTAKE][ACADEMIC]"
INTAKE_BODY_FIELDS = (
    "Batch ID",
    "Search and provenance log",
    "Candidate records",
    "Safeguards",
)


def api_get(url: str, token: str) -> tuple[object, str | None]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "criminal-infiltration-research-metrics",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload, response.headers.get("Link")


def next_link(value: str | None) -> str | None:
    if not value:
        return None
    for part in value.split(","):
        match = re.match(r'\s*<([^>]+)>;\s*rel="([^"]+)"', part)
        if match and match.group(2) == "next":
            return match.group(1)
    return None


def extract_run(body: str) -> dict | None:
    if MARKER not in body:
        return None
    matches = JSON_BLOCK.findall(body)
    if len(matches) != 1:
        raise MetricsError("Marked ledger comment must contain exactly one JSON block")
    try:
        payload = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise MetricsError("Marked ledger comment contains invalid JSON") from exc
    return validate_run(payload)


def issue_form_value(body: str, label: str) -> str | None:
    """Return the first non-empty value under one GitHub issue-form heading."""
    pattern = re.compile(
        rf"(?m)^###\s+{re.escape(label)}\s*$\n+(?P<value>.*?)(?=^###\s+|\Z)",
        re.DOTALL,
    )
    match = pattern.search(body.replace("\r\n", "\n"))
    if not match:
        return None
    value = match.group("value").strip()
    return value or None


def verify_intake_issue(
    run: dict,
    issue: dict,
    allowed_authors: set[str],
    ledger_issue_number: int,
) -> None:
    """Bind a positive candidate count to its real, batch-specific intake issue."""
    intake = run["intake_issue"]
    if not intake["created"]:
        return

    number = intake["number"]
    batch_id = run["batch_id"]
    canonical_url = f"https://github.com/{REPOSITORY_FULL_NAME}/issues/{number}"
    if number == ledger_issue_number:
        raise MetricsError("run.intake_issue: metrics ledger cannot be an intake issue")
    if issue.get("pull_request") is not None:
        raise MetricsError("run.intake_issue: referenced object is a pull request")
    if issue.get("number") != number or issue.get("html_url") != canonical_url:
        raise MetricsError("run.intake_issue: fetched issue identity disagrees with run")
    author = ((issue.get("user") or {}).get("login") or "").strip()
    if author not in allowed_authors:
        raise MetricsError("run.intake_issue: issue author is not authorised")
    if issue.get("title") != f"{INTAKE_TITLE_PREFIX} {batch_id}":
        raise MetricsError("run.intake_issue: title does not identify this batch")

    body = issue.get("body")
    if not isinstance(body, str):
        raise MetricsError("run.intake_issue: issue body is missing")
    values = {label: issue_form_value(body, label) for label in INTAKE_BODY_FIELDS}
    if any(value is None for value in values.values()):
        raise MetricsError("run.intake_issue: candidate-intake form is incomplete")
    if values["Batch ID"] != batch_id:
        raise MetricsError("run.intake_issue: issue batch ID disagrees with run")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--allowed-author", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()
    if args.repository != REPOSITORY_FULL_NAME:
        raise MetricsError("repository must match the governed repository")
    token = os.environ.get(args.token_env)
    if not token:
        raise MetricsError(f"Missing token environment variable {args.token_env}")

    url = (
        f"https://api.github.com/repos/{args.repository}/issues/"
        f"{args.issue}/comments?per_page=100"
    )
    comments: list[dict] = []
    while url:
        page, links = api_get(url, token)
        if not isinstance(page, list):
            raise MetricsError("GitHub comments response is not a list")
        comments.extend(page)
        url = next_link(links)

    runs = []
    intake_cache: dict[int, dict] = {}
    allowed_authors = set(args.allowed_author)
    for comment in comments:
        body = comment.get("body") or ""
        if MARKER not in body:
            continue
        author = ((comment.get("user") or {}).get("login") or "").strip()
        if author not in allowed_authors:
            continue
        run = extract_run(body)
        if run is None:
            continue
        intake = run["intake_issue"]
        if intake["created"]:
            number = intake["number"]
            if number not in intake_cache:
                issue_url = (
                    f"https://api.github.com/repos/{args.repository}/issues/{number}"
                )
                issue, _ = api_get(issue_url, token)
                if not isinstance(issue, dict):
                    raise MetricsError("GitHub intake issue response is not an object")
                intake_cache[number] = issue
            verify_intake_issue(run, intake_cache[number], allowed_authors, args.issue)
        runs.append(run)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"runs": runs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Fetched {len(runs)} validated surveillance run(s) from issue #{args.issue}.")


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, MetricsError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
