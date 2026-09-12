#!/usr/bin/env python3
"""Recover every open governed intake not yet represented in the curator queue.

Recovery is deliberately sequential.  Earlier intake issues are staged first so
later rediscoveries reconcile against the state produced by earlier batches.  A
failure in one issue is recorded and does not erase successfully staged earlier
batches; unresolved failures remain open for explicit repair.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from fetch_surveillance_ledger import api_get, next_link  # noqa: E402
from fetch_surveillance_ledger_quarantine import (  # noqa: E402
    PERMANENTLY_QUARANTINED_BATCHES,
    fetch_validated_run_for_intake,
)
from scripts.curation.stage_intake import IntakeImportError, stage_candidates  # noqa: E402

PREFIX = "[INTAKE][ACADEMIC] "


def paginated_issues(repository: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repository}/issues?state=open&per_page=100&sort=created&direction=asc"
    rows: list[dict] = []
    while url:
        page, links = api_get(url, token)
        if not isinstance(page, list):
            raise RuntimeError("GitHub issues response is not a list")
        rows.extend(item for item in page if isinstance(item, dict) and item.get("pull_request") is None)
        url = next_link(links)
    return rows


def represented_batches(root: Path) -> set[str]:
    represented = {
        path.stem
        for path in (root / "data/curation/intake_access").glob("ACADEMIC-*.json")
    }
    queue = root / "data/curation/review_queue.csv"
    if queue.exists():
        with queue.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                for token in (row.get("provenance") or "").split(";"):
                    if token.startswith("batch:ACADEMIC-"):
                        represented.add(token[len("batch:"):])
    return represented


def recover(
    root: Path,
    repository: str,
    token: str,
    owner: str,
    ledger_issue: int,
    imported_at: str,
) -> dict:
    cycle = json.loads((root / "config/archive-cycle.json").read_text())
    ceiling = int(cycle["legacy_issue_ceiling"])
    represented = represented_batches(root)
    processed: list[dict] = []
    quarantined: list[dict] = []
    failures: list[dict] = []
    ignored: list[dict] = []

    issues = sorted(paginated_issues(repository, token), key=lambda item: int(item["number"]))
    for issue in issues:
        number = int(issue["number"])
        title = str(issue.get("title") or "")
        if number <= ceiling or not title.startswith(PREFIX):
            continue
        batch_id = title[len(PREFIX):].strip()
        if batch_id in PERMANENTLY_QUARANTINED_BATCHES:
            quarantined.append(
                {
                    "issue_number": number,
                    "batch_id": batch_id,
                    "reason": "audited permanently quarantined duplicate/invalid surveillance batch",
                }
            )
            continue
        if batch_id in represented:
            ignored.append(
                {
                    "issue_number": number,
                    "batch_id": batch_id,
                    "reason": "already represented in queue or intake-access snapshot",
                }
            )
            continue
        try:
            run = fetch_validated_run_for_intake(
                repository, ledger_issue, [owner], token, cycle, issue
            )
            if run is None:
                raise IntakeImportError("authenticated completed terminal is absent")
            result = stage_candidates(
                root,
                issue.get("body") or "",
                title,
                str(number),
                imported_at,
                issue_created_at=issue.get("created_at"),
                run=run,
            )
            processed.append(result)
            # A batch with additions has a snapshot/provenance marker. A
            # rediscovery-only batch is intentionally represented only by its
            # immutable source issue plus this recovery audit.
            if result["added"]:
                represented.add(batch_id)
        except Exception as exc:  # keep unrelated batches recoverable
            failures.append(
                {
                    "issue_number": number,
                    "batch_id": batch_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    return {
        "processed": processed,
        "quarantined": quarantined,
        "failures": failures,
        "ignored": ignored,
        "processed_batches": len(processed),
        "added_candidates": sum(len(row["added"]) for row in processed),
        "rediscovery_occurrences": sum(len(row["skipped_existing"]) for row in processed),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ledger-issue", type=int, default=30)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise SystemExit("[RECOVERY BLOCKED] GH_TOKEN is required")
    result = recover(
        args.root.resolve(),
        args.repository,
        token,
        args.owner,
        args.ledger_issue,
        args.date,
    )
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"[OK] Recovery staged {result['added_candidates']} candidate(s) from "
        f"{result['processed_batches']} batch(es), reconciled "
        f"{result['rediscovery_occurrences']} rediscovery occurrence(s), with "
        f"{len(result['failures'])} unresolved batch(es)."
    )


if __name__ == "__main__":
    main()
