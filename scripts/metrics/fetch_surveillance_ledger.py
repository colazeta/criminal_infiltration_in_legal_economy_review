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


def api_get(url: str, token: str) -> tuple[list[dict], str | None]:
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
        if not isinstance(payload, list):
            raise MetricsError("GitHub comments response is not a list")
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
        comments.extend(page)
        url = next_link(links)

    runs = []
    for comment in comments:
        body = comment.get("body") or ""
        if MARKER not in body:
            continue
        author = ((comment.get("user") or {}).get("login") or "").strip()
        if author not in args.allowed_author:
            continue
        run = extract_run(body)
        if run is None:
            continue
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
