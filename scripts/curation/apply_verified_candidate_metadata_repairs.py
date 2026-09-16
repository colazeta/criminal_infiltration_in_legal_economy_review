#!/usr/bin/env python3
"""Apply reviewed explicit bibliographic repairs to queue-owned CandidateRecords.

This is a metadata-verifier extension of the existing candidate metadata
reconciliation workflow. It consumes a reviewed, append-only-style declaration
file and writes only bibliographic fields plus mechanical verification state in
``data/curation/review_queue.csv``. It never changes screening decisions,
canonical identity, publication state or scientific labels.

Every declaration is fail-closed: it must bind the exact pre-repair queue values,
contain at least two named evidence sources, and may replace only the closed set
of bibliographic fields below. A stale declaration is an error, not permission to
silently overwrite newer queue state.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
DECLARATIONS = Path("data/curation/verified_candidate_metadata_repairs.json")
QUEUE = Path("data/curation/review_queue.csv")
ALLOWED_REPLACEMENT_FIELDS = {
    "title",
    "doi",
    "authors",
    "year",
    "venue",
    "work_type",
    "source_links",
}
REQUIRED_EXPECTED_FIELDS = {
    "title",
    "doi",
    "authors",
    "year",
    "venue",
    "verification_status",
    "metadata_confidence",
    "review_stage",
    "current_status",
    "current_decision",
    "possible_duplicate",
    "metadata_conflict",
}


class VerifiedMetadataRepairError(ValueError):
    """Raised when a reviewed repair declaration is unsafe or stale."""


def clean(value: Any) -> str:
    return str(value or "").strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise VerifiedMetadataRepairError(f"{path} has no header")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _valid_https_url(value: Any) -> bool:
    try:
        parsed = urlsplit(clean(value))
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def load_declarations(root: Path) -> list[dict[str, Any]]:
    path = root / DECLARATIONS
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerifiedMetadataRepairError(f"invalid verified candidate metadata repair ledger: {exc}") from exc
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("repairs"), list):
        raise VerifiedMetadataRepairError("verified candidate metadata repair ledger has invalid schema")

    declarations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in payload["repairs"]:
        if not isinstance(raw, dict):
            raise VerifiedMetadataRepairError("verified candidate metadata repair entry is not an object")
        candidate_id = clean(raw.get("candidate_id"))
        if not candidate_id or candidate_id in seen:
            raise VerifiedMetadataRepairError("blank or duplicate verified metadata repair candidate")
        seen.add(candidate_id)

        expected = raw.get("expected")
        replacement = raw.get("replacement")
        evidence = raw.get("evidence")
        basis = clean(raw.get("basis"))
        checked_at = clean(raw.get("checked_at"))
        if not isinstance(expected, dict) or not isinstance(replacement, dict):
            raise VerifiedMetadataRepairError(f"repair lacks expected/replacement object: {candidate_id}")
        if set(expected) != REQUIRED_EXPECTED_FIELDS:
            raise VerifiedMetadataRepairError(f"repair expected fields are not closed: {candidate_id}")
        if not replacement or not set(replacement).issubset(ALLOWED_REPLACEMENT_FIELDS):
            raise VerifiedMetadataRepairError(f"repair replacement fields are not allowed: {candidate_id}")
        if any(not isinstance(value, (str, int)) for value in replacement.values()):
            raise VerifiedMetadataRepairError(f"repair replacement values must be scalar: {candidate_id}")
        if not isinstance(evidence, list) or len(evidence) < 2:
            raise VerifiedMetadataRepairError(f"repair needs at least two evidence sources: {candidate_id}")
        roles: set[str] = set()
        urls: set[str] = set()
        for source in evidence:
            if not isinstance(source, dict):
                raise VerifiedMetadataRepairError(f"repair evidence is not an object: {candidate_id}")
            role = clean(source.get("role"))
            url = clean(source.get("url"))
            if not role or not _valid_https_url(url):
                raise VerifiedMetadataRepairError(f"repair evidence is incomplete or unsafe: {candidate_id}")
            roles.add(role)
            urls.add(url)
        if len(urls) < 2 or "primary_metadata" not in roles:
            raise VerifiedMetadataRepairError(f"repair evidence is not independently grounded: {candidate_id}")
        if not basis:
            raise VerifiedMetadataRepairError(f"repair lacks provenance basis: {candidate_id}")
        try:
            checked_at = date.fromisoformat(checked_at).isoformat()
        except ValueError as exc:
            raise VerifiedMetadataRepairError(f"repair has invalid checked_at: {candidate_id}") from exc

        declarations.append(
            {
                "candidate_id": candidate_id,
                "expected": {key: clean(value) for key, value in expected.items()},
                "replacement": {key: clean(value) for key, value in replacement.items()},
                "evidence": evidence,
                "basis": basis,
                "checked_at": checked_at,
            }
        )
    return declarations


def find_safe_repairs(queue_rows: list[dict[str, str]], declarations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue = {clean(row.get("candidate_id")): row for row in queue_rows}
    if "" in queue or len(queue) != len(queue_rows):
        raise VerifiedMetadataRepairError("blank or duplicate candidate in review queue")

    repairs: list[dict[str, Any]] = []
    for declaration in declarations:
        candidate_id = declaration["candidate_id"]
        row = queue.get(candidate_id)
        if row is None:
            raise VerifiedMetadataRepairError(f"repair candidate is absent from review queue: {candidate_id}")
        if clean(row.get("origin")) != "daily_surveillance":
            raise VerifiedMetadataRepairError(f"repair candidate is not surveillance-owned: {candidate_id}")
        if clean(row.get("current_status")) != "pending" or clean(row.get("current_decision")):
            raise VerifiedMetadataRepairError(f"repair candidate already has a governed decision: {candidate_id}")

        target_state = {
            **declaration["replacement"],
            "verification_status": "metadata_verified",
            "metadata_confidence": "high",
            "review_stage": "abstract_full_text_review",
        }
        if all(clean(row.get(field)) == clean(value) for field, value in target_state.items()):
            continue

        stale = [
            field
            for field, expected in declaration["expected"].items()
            if clean(row.get(field)) != clean(expected)
        ]
        if stale:
            raise VerifiedMetadataRepairError(
                f"repair declaration is stale for {candidate_id}: " + ", ".join(sorted(stale))
            )
        if clean(row.get("verification_status")) != "metadata_partial" or clean(row.get("review_stage")) != "metadata_fix":
            raise VerifiedMetadataRepairError(f"repair candidate is not at the metadata repair gate: {candidate_id}")
        if clean(row.get("possible_duplicate")) or clean(row.get("metadata_conflict")):
            raise VerifiedMetadataRepairError(f"repair candidate retains unresolved identity metadata: {candidate_id}")
        repairs.append(declaration)
    return repairs


def apply_repairs(queue_rows: list[dict[str, str]], repairs: list[dict[str, Any]], updated_at: str) -> None:
    repair_by_id = {repair["candidate_id"]: repair for repair in repairs}
    for row in queue_rows:
        repair = repair_by_id.get(clean(row.get("candidate_id")))
        if repair is None:
            continue
        for field, value in repair["replacement"].items():
            row[field] = clean(value)
        row["verification_status"] = "metadata_verified"
        row["metadata_confidence"] = "high"
        row["review_stage"] = "abstract_full_text_review"
        row["updated_at"] = updated_at


def reconcile(root: Path, updated_at: str, *, check: bool = False) -> dict[str, Any]:
    updated_at = date.fromisoformat(updated_at).isoformat()
    fields, queue_rows = read_csv(root / QUEUE)
    missing = ({"candidate_id", "origin", "updated_at"} | REQUIRED_EXPECTED_FIELDS | ALLOWED_REPLACEMENT_FIELDS) - set(fields)
    if missing:
        raise VerifiedMetadataRepairError("review queue missing field(s): " + ", ".join(sorted(missing)))
    declarations = load_declarations(root)
    repairs = find_safe_repairs(queue_rows, declarations)
    summary = {
        "schema_version": 1,
        "safe_verified_metadata_repairs": len(repairs),
        "candidate_ids": [repair["candidate_id"] for repair in repairs],
        "repairs": [
            {
                "candidate_id": repair["candidate_id"],
                "replacement": repair["replacement"],
                "checked_at": repair["checked_at"],
                "evidence_urls": [source["url"] for source in repair["evidence"]],
            }
            for repair in repairs
        ],
        "scientific_decisions_changed": 0,
        "canonical_records_changed": 0,
        "publication_records_changed": 0,
    }
    if check:
        if repairs:
            raise VerifiedMetadataRepairError(
                "reviewed candidate metadata repair(s) remain unapplied: " + ", ".join(summary["candidate_ids"])
            )
        return summary
    if repairs:
        apply_repairs(queue_rows, repairs, updated_at)
        write_csv(root / QUEUE, fields, queue_rows)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--date", dest="updated_at", default=date.today().isoformat())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = reconcile(args.root.resolve(), args.updated_at, check=args.check)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, csv.Error, VerifiedMetadataRepairError) as exc:
        raise SystemExit(f"[VERIFIED METADATA REPAIR BLOCKED] {exc}") from exc
