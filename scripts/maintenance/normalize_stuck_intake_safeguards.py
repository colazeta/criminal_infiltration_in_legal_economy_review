#!/usr/bin/env python3
"""One-shot repair for malformed surveillance-intake safeguard sections.

This maintenance utility is intentionally narrow. It changes only the final
``### Safeguards`` section of an explicit allow-list of already-created
academic intake issues. Search manifests, CandidateRecords, batch IDs and all
preceding issue-body bytes are preserved exactly.

It exists to recover intake issues whose safeguards expressed the intended
checks with non-canonical wording or an extra confirmation. The governed ledger
validator requires exactly the three canonical confirmations below.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TARGET_ISSUES = (338, 339, 340, 341, 342, 348, 349, 350, 351, 352, 584)
HEADING = "### Safeguards"
CANONICAL_SECTION = """### Safeguards

- [x] No candidate was marked eligible or published.
- [x] Canonical records and existing intake issues were checked for duplicates.
- [x] No copyrighted full text or long abstract is included."""


def api(method: str, url: str, token: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cile-intake-safeguard-recovery",
        },
    )
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def normalized_body(body: str) -> tuple[str, bool]:
    if body.count(HEADING) != 1:
        raise RuntimeError("issue body must contain exactly one Safeguards heading")
    prefix, _old = body.split(HEADING, 1)
    if not prefix.rstrip().endswith("```"):
        raise RuntimeError("Safeguards must be the final section after a fenced manifest")
    replacement = prefix.rstrip() + "\n\n" + CANONICAL_SECTION
    return replacement, replacement != body.rstrip()


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repository:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")

    base = f"https://api.github.com/repos/{repository}/issues"
    changed = 0
    for number in TARGET_ISSUES:
        before = api("GET", f"{base}/{number}", token)
        title = str(before.get("title") or "")
        body = str(before.get("body") or "")
        if not title.startswith("[INTAKE][ACADEMIC] ACADEMIC-"):
            raise RuntimeError(f"#{number}: unexpected title {title!r}")

        replacement, needs_change = normalized_body(body)
        prefix_before = body.split(HEADING, 1)[0].rstrip()
        prefix_after = replacement.split(HEADING, 1)[0].rstrip()
        if prefix_before != prefix_after:
            raise RuntimeError(f"#{number}: non-safeguard content changed before PATCH")

        if needs_change:
            api("PATCH", f"{base}/{number}", token, {"body": replacement})
            changed += 1

        after = api("GET", f"{base}/{number}", token)
        after_body = str(after.get("body") or "").rstrip()
        if after_body != replacement:
            raise RuntimeError(f"#{number}: persisted body does not match requested repair")
        if after_body.split(HEADING, 1)[0].rstrip() != prefix_before:
            raise RuntimeError(f"#{number}: persisted non-safeguard content changed")
        if not after_body.endswith(CANONICAL_SECTION):
            raise RuntimeError(f"#{number}: canonical safeguards not persisted")
        print(f"#{number}: {'repaired' if needs_change else 'already canonical'}")

    print(f"normalization complete: {changed} issue(s) changed")


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
