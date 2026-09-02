#!/usr/bin/env python3
"""Reconcile automatic access classification with retrieval conflicts and assisted evidence.

This layer is deliberately conservative:
- a closed-metadata classification is downgraded to `unknown` when the governed
  retrieval ledger also contains a full-text locator that could not be verified by
  the automated probe;
- explicit assisted evidence may upgrade a candidate to `open` only;
- assisted evidence may never force a candidate to `restricted`.

No article or abstract text is persisted.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data" / "curation" / "review_queue.csv"
RETRIEVAL_PATH = ROOT / "data" / "curation" / "retrieval_coverage.csv"
COVERAGE_PATH = ROOT / "data" / "curation" / "access_coverage.csv"
EVIDENCE_PATH = ROOT / "data" / "curation" / "access_evidence.csv"

ACCESS_FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "access_status",
    "access_kind",
    "access_url",
    "evidence_source",
    "evidence_detail",
    "checked_at",
    "notes",
]
EVIDENCE_FIELDS = [
    "candidate_id",
    "access_status",
    "access_kind",
    "access_url",
    "evidence_source",
    "evidence_detail",
    "verified_at",
]


class EvidenceError(ValueError):
    pass


def clean(value: object, maximum: int = 2000) -> str:
    return " ".join(str(value or "").split())[:maximum]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def rows_by_candidate(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read_csv(path)
    return {row.get("candidate_id", ""): row for row in rows if row.get("candidate_id")}


def valid_https_url(value: object) -> bool:
    try:
        parsed = urlsplit(clean(value, 2000))
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_evidence(queue_ids: set[str], fields: list[str], rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    if fields != EVIDENCE_FIELDS:
        raise EvidenceError(f"access_evidence_fields_mismatch:{fields}")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = clean(row.get("candidate_id"), 80)
        if candidate_id not in queue_ids:
            raise EvidenceError(f"access_evidence_unknown_candidate:{candidate_id}")
        if candidate_id in result:
            raise EvidenceError(f"access_evidence_duplicate_candidate:{candidate_id}")
        if row.get("access_status") != "open":
            raise EvidenceError(f"assisted_evidence_may_only_confirm_open:{candidate_id}")
        if not clean(row.get("access_kind"), 100):
            raise EvidenceError(f"access_evidence_missing_kind:{candidate_id}")
        if not valid_https_url(row.get("access_url")):
            raise EvidenceError(f"access_evidence_invalid_url:{candidate_id}")
        if not clean(row.get("evidence_source"), 300) or not clean(row.get("evidence_detail"), 1200):
            raise EvidenceError(f"access_evidence_missing_provenance:{candidate_id}")
        if not clean(row.get("verified_at"), 20):
            raise EvidenceError(f"access_evidence_missing_date:{candidate_id}")
        result[candidate_id] = row
    return result


def append_note(existing: str, note: str) -> str:
    parts = [clean(existing, 1200), clean(note, 1200)]
    return "; ".join(part for part in parts if part)


def reconcile(
    queue: list[dict[str, str]],
    coverage: list[dict[str, str]],
    retrieval: dict[str, dict[str, str]],
    evidence: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    if len(queue) != len(coverage):
        raise EvidenceError(f"access_count_mismatch:{len(coverage)}:{len(queue)}")
    output: list[dict[str, str]] = []
    changes = {"assisted_open": 0, "conflict_to_unknown": 0}
    for candidate, current in zip(queue, coverage, strict=True):
        candidate_id = candidate.get("candidate_id", "")
        if current.get("candidate_id") != candidate_id:
            raise EvidenceError(f"access_order_mismatch:{current.get('candidate_id')}:{candidate_id}")
        row = dict(current)
        governed = retrieval.get(candidate_id, {})
        assisted = evidence.get(candidate_id)

        # A resolver-level full-text locator conflicts with a metadata-only closed
        # result when the anonymous runtime probe could not verify the manifestation.
        # Preserve uncertainty rather than overstate restriction.
        if (
            row.get("access_status") == "restricted"
            and row.get("access_kind") == "closed_metadata"
            and clean(governed.get("full_text_url"), 2000).startswith("https://")
        ):
            row.update(
                {
                    "access_status": "unknown",
                    "access_kind": "conflicting_full_text_evidence",
                    "access_url": clean(governed.get("full_text_url"), 2000),
                    "evidence_source": "Retrieval + closed metadata conflict",
                    "evidence_detail": (
                        "The resolver has a candidate-bound full-text locator, but the automated anonymous probe did not verify it while scholarly metadata reports closed access."
                    ),
                    "notes": append_note(row.get("notes", ""), "Do not infer restriction until the full-text locator is resolved by another access check."),
                }
            )
            changes["conflict_to_unknown"] += 1

        # Positive observed access is stronger than both unknown and closed metadata.
        if assisted:
            row.update(
                {
                    "access_status": "open",
                    "access_kind": clean(assisted.get("access_kind"), 100),
                    "access_url": clean(assisted.get("access_url"), 2000),
                    "evidence_source": clean(assisted.get("evidence_source"), 300),
                    "evidence_detail": clean(assisted.get("evidence_detail"), 1200),
                    "checked_at": clean(assisted.get("verified_at"), 20),
                    "notes": append_note(row.get("notes", ""), "Positive access independently verified by assisted web research."),
                }
            )
            changes["assisted_open"] += 1

        output.append(row)
    return output, changes


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACCESS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=Path, default=COVERAGE_PATH)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    queue_fields, queue = read_csv(QUEUE_PATH)
    del queue_fields
    coverage_fields, coverage = read_csv(args.coverage)
    if coverage_fields != ACCESS_FIELDS:
        raise SystemExit(f"access_coverage_fields_mismatch:{coverage_fields}")
    evidence_fields, evidence_rows = read_csv(args.evidence)
    queue_ids = {row.get("candidate_id", "") for row in queue}
    evidence = validate_evidence(queue_ids, evidence_fields, evidence_rows)
    retrieval = rows_by_candidate(RETRIEVAL_PATH)
    reconciled, changes = reconcile(queue, coverage, retrieval, evidence)

    if args.check:
        if reconciled != coverage:
            raise SystemExit("access_coverage_not_reconciled")
        print(changes)
        return

    write_csv(reconciled, args.coverage)
    print(changes)


if __name__ == "__main__":
    main()
