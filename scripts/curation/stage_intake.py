#!/usr/bin/env python3
"""Stage one authenticated intake without letting rediscovery poison the batch.

The GitHub intake issue remains the immutable occurrence record.  This module
adds only candidate identities not already represented in the operational queue
or canonical registries.  Exact DOI/stable-identifier/citation collisions are
reported as rediscoveries; they are not scientific duplicate decisions and do
not alter canonical identity.  Conflicting exact identifiers fail closed.

Access snapshots contain the original receipts for candidates actually added to
the operational queue.  Rediscovered occurrences remain preserved in the source
issue and in the returned reconciliation audit rather than creating duplicate
candidate rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from scripts.curation.import_intake_issue import (
    ROOT,
    IntakeImportError,
    clean,
    normalise_doi,
    parse_intake_issue,
    read_queue,
)
from scripts.intake_open_access import validate_cycle, validate_intake_access
from scripts.surveillance_identity import batch_day, candidate_keys


def _normal(value: object) -> str:
    return " ".join(
        re.findall(r"\w+", unicodedata.normalize("NFKC", str(value)).casefold())
    )


def _candidate_from_queue(row: dict[str, str]) -> dict:
    return {
        "title": row.get("title") or "",
        "authors": [x.strip() for x in (row.get("authors") or "").split(";") if x.strip()],
        "year": int(row["year"]) if (row.get("year") or "").isdigit() else None,
        "identifiers": {
            "doi": row.get("doi") or None,
            "other": [
                x.strip()
                for x in (row.get("other_identifiers") or "").split(";")
                if x.strip()
            ],
        },
    }


def _candidate_from_paper(row: dict[str, str]) -> dict:
    return {
        "title": row.get("title") or "",
        "authors": [x.strip() for x in (row.get("authors") or "").split(";") if x.strip()],
        "year": int(row["year"]) if (row.get("year") or "").isdigit() else None,
        "identifiers": {"doi": row.get("doi") or None, "other": []},
    }


def _render_key(key: tuple) -> str:
    return ":".join(str(value) for value in key)


def _inventory(root: Path, queue: list[dict[str, str]]):
    key_targets: dict[tuple, set[str]] = defaultdict(set)
    titles: dict[str, str] = {}

    def add(target: str, candidate: dict) -> None:
        titles[target] = str(candidate.get("title") or "")
        for key in candidate_keys(candidate):
            key_targets[key].add(target)

    for row in queue:
        add(f"candidate:{row['candidate_id']}", _candidate_from_queue(row))

    papers: dict[str, dict] = {}
    papers_path = root / "data/registry/papers.csv"
    if papers_path.exists():
        with papers_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                paper_id = (row.get("paper_id") or "").strip()
                if not paper_id:
                    continue
                candidate = _candidate_from_paper(row)
                papers[paper_id] = candidate
                add(f"paper:{paper_id}", candidate)

    identifiers_path = root / "data/registry/work_identifiers.csv"
    if identifiers_path.exists():
        with identifiers_path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                paper_id = (row.get("paper_id") or row.get("work_id") or "").strip()
                scheme = (row.get("scheme") or "").strip().casefold()
                value = (row.get("value") or "").strip()
                if not paper_id or not value:
                    continue
                target = f"paper:{paper_id}"
                if target not in titles:
                    titles[target] = str((papers.get(paper_id) or {}).get("title") or "")
                values = [value, f"{scheme}:{value}"] if scheme else [value]
                for key in candidate_keys({"identifiers": {"doi": value if scheme == "doi" else None, "other": [] if scheme == "doi" else values}}):
                    key_targets[key].add(target)
    return key_targets, titles


def reconcile_candidates(root: Path, queue: list[dict[str, str]], candidates: list[dict]):
    """Return novel candidates plus exact rediscovery observations.

    Matching is deliberately limited to the existing exact collision keys.  An
    approximate-title match is never used to suppress a candidate.
    """
    key_targets, titles = _inventory(root, queue)
    novel: list[dict] = []
    skipped: list[dict] = []

    for candidate in candidates:
        keys = candidate_keys(candidate)
        matches: set[str] = set()
        matched_keys: list[tuple] = []
        for key in keys:
            targets = key_targets.get(key, set())
            if targets:
                matches.update(targets)
                matched_keys.append(key)

        if matches:
            incoming_title = _normal(candidate.get("title") or "")
            strong = [key for key in matched_keys if key and key[0] in {"doi", "id"}]
            if strong and incoming_title:
                existing_titles = {
                    _normal(titles.get(target, ""))
                    for target in matches
                    if _normal(titles.get(target, ""))
                }
                if existing_titles and incoming_title not in existing_titles:
                    raise IntakeImportError(
                        "Exact identifier collides with an incompatible title; human reconciliation required"
                    )
            skipped.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "existing_ids": sorted(matches),
                    "matched_keys": sorted(_render_key(key) for key in matched_keys),
                }
            )
            continue

        novel.append(candidate)
        target = f"candidate:{candidate['candidate_id']}"
        titles[target] = str(candidate.get("title") or "")
        for key in keys:
            key_targets[key].add(target)

    return novel, skipped


def _validate_context(
    root: Path,
    body: str,
    issue_title: str,
    issue_number: str,
    imported_at: str,
    issue_created_at: str | None,
    run: dict | None,
):
    try:
        imported_at = date.fromisoformat(imported_at).isoformat()
    except ValueError as exc:
        raise IntakeImportError("Import date must use YYYY-MM-DD") from exc
    if not re.fullmatch(r"\d+", issue_number):
        raise IntakeImportError("GitHub issue number is invalid")

    manifest = parse_intake_issue(body, issue_title)
    batch_date = batch_day(manifest["batch_id"])
    created_at = (
        datetime.fromisoformat(issue_created_at.replace("Z", "+00:00"))
        if issue_created_at
        else None
    )
    cycle_path = root / "config/archive-cycle.json"
    try:
        if cycle_path.exists():
            cycle = json.loads(cycle_path.read_text())
            if int(issue_number) <= cycle["legacy_issue_ceiling"]:
                raise ValueError("This intake belongs to the retired archive")
            validate_cycle(
                batch_date,
                issue_number,
                created_at,
                cycle,
                batch_id=manifest["batch_id"],
            )
            if run is None:
                raise ValueError("validated completed ledger run required before queue import")
        if run is not None:
            if (
                run.get("schema_version") != manifest["schema_version"]
                or run.get("batch_id") != manifest["batch_id"]
                or run.get("status") != "completed"
                or (run.get("intake_issue") or {}).get("number") != int(issue_number)
            ):
                raise ValueError("completed ledger run does not identify this intake")
            started = datetime.fromisoformat(run["window_start"].replace("Z", "+00:00"))
            ended = datetime.fromisoformat(run["window_end"].replace("Z", "+00:00"))
            if created_at is None or not started <= created_at <= ended:
                raise ValueError("issue creation is outside validated run window")
        if created_at is not None:
            for candidate in manifest["candidates"]:
                validate_intake_access(
                    candidate["open_access"],
                    candidate,
                    batch_date,
                    observed_by=created_at,
                    allow_pending=manifest["schema_version"] == 3,
                )
    except (ValueError, TypeError) as exc:
        raise IntakeImportError(str(exc)) from exc
    if date.fromisoformat(imported_at) < batch_date:
        raise IntakeImportError("Import date cannot precede the intake batch")
    return manifest, imported_at


def _row_for_candidate(
    fields: list[str], candidate: dict, issue_number: str, batch_id: str, imported_at: str
) -> dict[str, str]:
    identifiers = candidate["identifiers"]
    verification = str(candidate["verification_status"])
    stage = (
        "metadata_fix"
        if verification != "metadata_verified" or candidate["metadata_conflict"]
        else "abstract_full_text_review"
    )
    row = {field: "" for field in fields}
    row.update(
        {
            "candidate_id": str(candidate["candidate_id"]),
            "title": clean(candidate["title"], 500),
            "doi": normalise_doi(identifiers["doi"]),
            "authors": "; ".join(clean(value, 300) for value in candidate["authors"]),
            "year": "" if candidate["year"] is None else str(candidate["year"]),
            "venue": clean(candidate["venue"], 300),
            "work_type": str(candidate["work_type"]),
            "source": " + ".join(clean(value, 40) for value in candidate["sources"]),
            "source_links": "; ".join(clean(value, 1000) for value in candidate["source_links"]),
            "other_identifiers": "; ".join(clean(value, 200) for value in identifiers["other"]),
            "source_query_id": "; ".join(clean(value, 80) for value in candidate["query_ids"]),
            "verification_status": verification,
            "metadata_confidence": "high" if verification == "metadata_verified" else "",
            "intake_assessment": str(candidate["intake_assessment"]),
            "intake_reason": clean(candidate["relevance_reason"], 1000),
            "possible_duplicate": clean(candidate["possible_duplicate"], 500),
            "metadata_conflict": clean(candidate["metadata_conflict"], 500),
            "required_human_action": clean(candidate["required_human_action"], 500),
            "origin": "daily_surveillance",
            "legacy_scope_fit": "",
            "legacy_recommendation": "",
            "legacy_reason": "",
            "legacy_priority": "",
            "review_stage": stage,
            "current_status": "pending",
            "current_decision": "",
            "exclusion_reason_code": "",
            "topic_code": "",
            "duplicate_target_id": "",
            "secondary_collection_code": "",
            "secondary_collection_rationale": "",
            "last_action_id": "",
            "materialised_at": imported_at,
            "updated_at": imported_at,
            "provenance": f"github-issue:#{issue_number};batch:{batch_id}",
        }
    )
    return row


def stage_candidates(
    root: Path,
    body: str,
    issue_title: str,
    issue_number: str,
    imported_at: str,
    *,
    issue_created_at: str | None = None,
    run: dict | None = None,
) -> dict[str, object]:
    manifest, imported_at = _validate_context(
        root, body, issue_title, issue_number, imported_at, issue_created_at, run
    )
    path = root / "data/curation/review_queue.csv"
    fields, queue = read_queue(path)
    required_fields = {
        "candidate_id", "title", "doi", "authors", "year", "venue", "work_type",
        "source", "source_links", "other_identifiers", "source_query_id",
        "verification_status", "intake_assessment", "intake_reason",
        "possible_duplicate", "metadata_conflict", "required_human_action",
        "origin", "review_stage", "current_status", "materialised_at", "updated_at",
        "provenance",
    }
    if required_fields - set(fields):
        raise IntakeImportError(
            "review_queue.csv is missing field(s): "
            + ", ".join(sorted(required_fields - set(fields)))
        )

    batch_id = str(manifest["batch_id"])
    batch_marker = f"batch:{batch_id}"
    candidates = list(manifest["candidates"])
    existing_ids = {row["candidate_id"] for row in queue}
    overlap = sorted(existing_ids & {str(c["candidate_id"]) for c in candidates})
    if overlap:
        raise IntakeImportError("Candidate(s) already materialised: " + ", ".join(overlap))
    if any(batch_marker in row.get("provenance", "").split(";") for row in queue):
        raise IntakeImportError(f"Intake batch {batch_id} is already staged")

    novel, skipped = reconcile_candidates(root, queue, candidates)
    for candidate in novel:
        queue.append(_row_for_candidate(fields, candidate, issue_number, batch_id, imported_at))
    queue.sort(key=lambda row: row["candidate_id"])

    snapshot_path = root / "data/curation/intake_access" / f"{batch_id}.json"
    if snapshot_path.exists():
        raise IntakeImportError(f"Intake batch {batch_id} already has an access snapshot")

    snapshot = None
    snapshot_bytes = None
    if novel:
        snapshot = {
            "schema_version": 2 if manifest["schema_version"] == 3 else 1,
            "batch_id": batch_id,
            "source_issue_number": int(issue_number),
            "source_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "receipts": [candidate["open_access"] for candidate in novel],
        }
        snapshot_bytes = (
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(queue)

    queue_changed = bool(novel)
    if queue_changed:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(buffer.getvalue())
    else:
        temporary = None

    created_snapshot = False
    try:
        if snapshot_bytes is not None:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=snapshot_path.parent, delete=False) as evidence:
                evidence_temp = Path(evidence.name)
                evidence.write(snapshot_bytes)
                evidence.flush()
                os.fsync(evidence.fileno())
            try:
                os.link(evidence_temp, snapshot_path)
                created_snapshot = True
            finally:
                evidence_temp.unlink(missing_ok=True)
        if temporary is not None:
            os.replace(temporary, path)
    except BaseException:
        if created_snapshot:
            snapshot_path.unlink(missing_ok=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    return {
        "batch_id": batch_id,
        "issue_number": int(issue_number),
        "added": [str(candidate["candidate_id"]) for candidate in novel],
        "skipped_existing": skipped,
        "queue_total": len(queue),
        "source_candidate_count": len(candidates),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--issue-body-file", type=Path, required=True)
    parser.add_argument("--issue-title-file", type=Path, required=True)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--issue-created-at", required=True)
    parser.add_argument("--date", dest="imported_at", required=True)
    parser.add_argument("--run-file", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = stage_candidates(
        args.root.resolve(),
        args.issue_body_file.read_text(encoding="utf-8"),
        args.issue_title_file.read_text(encoding="utf-8"),
        args.issue_number,
        args.imported_at,
        issue_created_at=args.issue_created_at,
        run=json.loads(args.run_file.read_text()),
    )
    if args.output:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"[OK] Staged {len(result['added'])} new candidate(s) from {result['batch_id']}; "
        f"reconciled {len(result['skipped_existing'])} exact rediscovery occurrence(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, json.JSONDecodeError, IntakeImportError) as exc:
        raise SystemExit(f"[INTAKE BLOCKED] {exc}") from exc
