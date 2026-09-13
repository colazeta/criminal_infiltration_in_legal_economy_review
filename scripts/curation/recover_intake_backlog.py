#!/usr/bin/env python3
"""Recover every open governed intake not yet reconciled with the curator queue.

Recovery is deliberately sequential. Earlier intake issues are staged first so
later rediscoveries reconcile against the state produced by earlier batches. A
failure in one issue is recorded and does not erase successfully staged earlier
batches; unresolved failures remain open for explicit repair.

A batch is never treated as preserved merely because *some* trace of the batch
already exists. Represented-but-open intakes are revalidated candidate by
candidate. They are finalised only when every source candidate is already
materialised or exactly reconciled to an existing operational/canonical identity;
otherwise the residual candidate is reported as an explicit blocker.

Stable DOI/identifier equality is the primary identity rule. A different observed
title under the same stable identifier is retained as audited manifestation
telemetry, not treated as a reason to duplicate or block an entire intake. Weak
citation/title matches remain secondary and conservative.

A terminal-absent historical intake can never create a new CandidateRecord. It
may be closed only when every source candidate is proven already represented by
existing operational/canonical identity. Any residual candidate remains an
explicit blocker until terminal evidence is repaired.

When new CandidateRecords are staged, their minimal retrieval/abstract/access
coverage projections are scaffolded before the preservation commit. This keeps
candidate conservation independent from network enrichment while preserving the
repository's one-to-one coverage invariant.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/metrics"))

from fetch_surveillance_ledger import api_get, next_link  # noqa: E402
from fetch_surveillance_ledger_quarantine import (  # noqa: E402
    PERMANENTLY_QUARANTINED_BATCHES,
    fetch_validated_run_for_intake,
)
from scripts.curation.import_intake_issue import parse_intake_issue, read_queue  # noqa: E402
from scripts.curation.audited_intake_reconciliation import audited_occurrences  # noqa: E402
from scripts.curation.scaffold_candidate_coverage import (  # noqa: E402
    COVERAGE_PATHS,
    scaffold_all,
)
import scripts.curation.stage_intake as stage_intake_module  # noqa: E402
from scripts.curation.stage_intake import (  # noqa: E402
    IntakeImportError,
    _inventory,
    _normal,
    _render_key,
    _validate_context,
)
from scripts.surveillance_identity import candidate_keys  # noqa: E402

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


def reconcile_candidates_stable_first(
    root: Path,
    queue: list[dict[str, str]],
    candidates: list[dict],
):
    """Reconcile exact stable IDs before title/citation observations."""
    key_targets, titles = _inventory(root, queue)
    novel: list[dict] = []
    skipped: list[dict] = []

    for candidate in candidates:
        keys = candidate_keys(candidate)
        strong_keys = [key for key in keys if key and key[0] in {"doi", "id"}]
        strong_matches: set[str] = set()
        matched_strong: list[tuple] = []
        for key in strong_keys:
            targets = key_targets.get(key, set())
            if targets:
                strong_matches.update(targets)
                matched_strong.append(key)

        if strong_matches:
            incoming_title = _normal(candidate.get("title") or "")
            existing_titles = sorted(
                {
                    _normal(titles.get(target, ""))
                    for target in strong_matches
                    if _normal(titles.get(target, ""))
                }
            )
            skipped.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "existing_ids": sorted(strong_matches),
                    "matched_keys": sorted(_render_key(key) for key in matched_strong),
                    "title_variant": bool(
                        incoming_title
                        and existing_titles
                        and incoming_title not in existing_titles
                    ),
                    "observed_title": str(candidate.get("title") or ""),
                    "existing_titles": existing_titles,
                }
            )
            continue

        weak_matches: set[str] = set()
        matched_weak: list[tuple] = []
        for key in keys:
            targets = key_targets.get(key, set())
            if targets:
                weak_matches.update(targets)
                matched_weak.append(key)
        if weak_matches:
            skipped.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "existing_ids": sorted(weak_matches),
                    "matched_keys": sorted(_render_key(key) for key in matched_weak),
                    "title_variant": False,
                }
            )
            continue

        novel.append(candidate)
        target = f"candidate:{candidate['candidate_id']}"
        titles[target] = str(candidate.get("title") or "")
        for key in keys:
            key_targets[key].add(target)

    return novel, skipped


def _stage_candidates_stable_first(*args, **kwargs):
    """Use stable-first reconciliation inside the existing strict stage contract."""
    original = stage_intake_module.reconcile_candidates
    stage_intake_module.reconcile_candidates = reconcile_candidates_stable_first
    try:
        return stage_intake_module.stage_candidates(*args, **kwargs)
    finally:
        stage_intake_module.reconcile_candidates = original


def _reconciliation_result(
    manifest: dict,
    issue_number: int,
    queue: list[dict[str, str]],
    skipped: list[dict],
    *,
    terminal_absent: bool = False,
) -> dict[str, object]:
    return {
        "batch_id": str(manifest["batch_id"]),
        "issue_number": issue_number,
        "added": [],
        "skipped_existing": skipped,
        "queue_total": len(queue),
        "source_candidate_count": len(manifest["candidates"]),
        "reconciliation_only": True,
        "terminal_absent": terminal_absent,
    }


def reconcile_represented_issue(
    root: Path,
    issue: dict,
    run: dict,
    imported_at: str,
) -> dict[str, object]:
    """Prove candidate conservation for an already-represented intake."""
    issue_number = str(issue["number"])
    issue_title = str(issue.get("title") or "")
    manifest, _ = _validate_context(
        root,
        issue.get("body") or "",
        issue_title,
        issue_number,
        imported_at,
        issue.get("created_at"),
        run,
    )
    _, queue = read_queue(root / "data/curation/review_queue.csv")
    queue_by_id = {row["candidate_id"]: row for row in queue}

    skipped: list[dict] = []
    remaining: list[dict] = []
    for candidate in manifest["candidates"]:
        candidate_id = str(candidate["candidate_id"])
        existing = queue_by_id.get(candidate_id)
        if existing is None:
            remaining.append(candidate)
            continue
        if _normal(existing.get("title") or "") != _normal(candidate.get("title") or ""):
            raise IntakeImportError(
                f"Candidate ID {candidate_id} is materialised with an incompatible title"
            )
        skipped.append(
            {
                "candidate_id": candidate_id,
                "existing_ids": [f"candidate:{candidate_id}"],
                "matched_keys": [f"candidate_id:{candidate_id}"],
                "title_variant": False,
            }
        )

    novel, exact_skipped = reconcile_candidates_stable_first(root, queue, remaining)
    skipped.extend(exact_skipped)
    if novel:
        unresolved = ", ".join(str(candidate["candidate_id"]) for candidate in novel)
        raise IntakeImportError(
            "represented batch still has unreconciled candidate identity/identities: "
            + unresolved
        )
    return _reconciliation_result(manifest, int(issue_number), queue, skipped)


def reconcile_terminal_absent_issue(
    root: Path,
    issue: dict,
    owner: str,
) -> dict[str, object]:
    """Close an orphan intake only if no new identity would be materialised."""
    author = ((issue.get("user") or {}).get("login") or "").strip()
    if author != owner:
        raise IntakeImportError("terminal-absent intake author is not the repository owner")
    title = str(issue.get("title") or "")
    manifest = parse_intake_issue(issue.get("body") or "", title)
    _, queue = read_queue(root / "data/curation/review_queue.csv")
    remaining, audited = audited_occurrences(issue, queue, list(manifest["candidates"]))
    novel, skipped = reconcile_candidates_stable_first(root, queue, remaining)
    skipped.extend(audited)
    if novel:
        unresolved = ", ".join(str(candidate["candidate_id"]) for candidate in novel)
        raise IntakeImportError(
            "authenticated completed terminal is absent; unreconciled source candidate(s): "
            + unresolved
        )
    return _reconciliation_result(
        manifest,
        int(issue["number"]),
        queue,
        skipped,
        terminal_absent=True,
    )


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
        try:
            run = fetch_validated_run_for_intake(
                repository, ledger_issue, [owner], token, cycle, issue
            )
            if run is None:
                result = reconcile_terminal_absent_issue(root, issue, owner)
            elif batch_id in represented:
                result = reconcile_represented_issue(root, issue, run, imported_at)
            else:
                result = _stage_candidates_stable_first(
                    root,
                    issue.get("body") or "",
                    title,
                    str(number),
                    imported_at,
                    issue_created_at=issue.get("created_at"),
                    run=run,
                )
            processed.append(result)
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


def _stage_coverage_for_preservation(root: Path) -> None:
    """Keep deterministic coverage projections in the same Actions commit."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    subprocess.run(
        ["git", "-C", str(root), "add", *[str(path) for path in COVERAGE_PATHS]],
        check=True,
    )


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
    root = args.root.resolve()
    result = recover(
        root,
        args.repository,
        token,
        args.owner,
        args.ledger_issue,
        args.date,
    )
    if result["added_candidates"]:
        result["coverage_placeholders"] = scaffold_all(root, args.date)
        _stage_coverage_for_preservation(root)
    else:
        result["coverage_placeholders"] = {
            "retrieval": 0,
            "abstract": 0,
            "access": 0,
        }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"[OK] Recovery staged {result['added_candidates']} candidate(s) from "
        f"{result['processed_batches']} batch(es), reconciled "
        f"{result['rediscovery_occurrences']} rediscovery occurrence(s), with "
        f"{len(result['failures'])} unresolved batch(es); "
        f"coverage placeholders: {result['coverage_placeholders']}."
    )


if __name__ == "__main__":
    main()
