#!/usr/bin/env python3
"""Materialise the legacy E0 evidence as a reviewable candidate queue.

The transformation preserves the pilot's statements as provenance. It never
turns a legacy recommendation into a screening or publication decision.
"""

from __future__ import annotations

import argparse
import csv
import io
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATERIALISED_AT = "2026-08-31"

FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "authors",
    "year",
    "venue",
    "work_type",
    "source",
    "source_links",
    "other_identifiers",
    "source_query_id",
    "verification_status",
    "metadata_confidence",
    "intake_assessment",
    "intake_reason",
    "possible_duplicate",
    "metadata_conflict",
    "required_human_action",
    "origin",
    "legacy_scope_fit",
    "legacy_recommendation",
    "legacy_reason",
    "legacy_priority",
    "review_stage",
    "current_status",
    "current_decision",
    "exclusion_reason_code",
    "topic_code",
    "duplicate_target_id",
    "secondary_collection_code",
    "secondary_collection_rationale",
    "last_action_id",
    "materialised_at",
    "updated_at",
    "provenance",
]

EXPECTED_STAGE_COUNTS = {
    "metadata_fix": 2,
    "manual_review": 9,
    "abstract_full_text_review": 25,
    "legacy_rejection_review": 19,
}
MUTABLE_FIELDS = {
    "current_status",
    "current_decision",
    "exclusion_reason_code",
    "topic_code",
    "duplicate_target_id",
    "secondary_collection_code",
    "secondary_collection_rationale",
    "last_action_id",
    "updated_at",
}


class QueueBuildError(ValueError):
    """Raised when the legacy evidence cannot be materialised safely."""


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise QueueBuildError(f"{path} has no header")
        return [dict(row) for row in reader]


def clean(value: str | None) -> str:
    return " ".join((value or "").split())


def normalise_doi(value: str | None) -> str:
    doi = clean(value).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi


def joined_reason(*parts: str | None) -> str:
    values: list[str] = []
    for part in parts:
        value = clean(part)
        if value and value not in values:
            values.append(value)
    return " | ".join(values)


def base_row(candidate_id: str) -> dict[str, str]:
    return {
        "candidate_id": candidate_id,
        "current_status": "pending",
        "current_decision": "",
        "exclusion_reason_code": "",
        "topic_code": "",
        "duplicate_target_id": "",
        "secondary_collection_code": "",
        "secondary_collection_rationale": "",
        "last_action_id": "",
        "materialised_at": MATERIALISED_AT,
        "updated_at": MATERIALISED_AT,
    }


def stage_for_candidate(
    candidate: dict[str, str], audit: dict[str, str] | None
) -> str:
    if audit:
        decision = clean(audit.get("pre_import_decision"))
        if decision == "import_after_metadata_fix":
            return "metadata_fix"
        if decision == "hold_for_manual_review":
            return "manual_review"
        if decision == "import_now":
            raise QueueBuildError(
                f"Already imported candidate leaked into queue: {candidate['candidate_id']}"
            )
    recommendation = clean(candidate.get("final_recommendation"))
    if recommendation == "keep_candidate_pending_abstract_review":
        return "abstract_full_text_review"
    if recommendation == "reject":
        return "legacy_rejection_review"
    raise QueueBuildError(
        f"No governed review stage for {candidate['candidate_id']}: {recommendation}"
    )


def materialise(root: Path = ROOT) -> list[dict[str, str]]:
    legacy = root / "data" / "legacy" / "e0"
    candidates = read_rows(legacy / "candidate_outcomes.csv")
    audit_rows = read_rows(legacy / "promotion_audit.csv")
    audit = {clean(row["seed_id"]): row for row in audit_rows}
    if len(audit) != len(audit_rows):
        raise QueueBuildError("promotion_audit.csv contains duplicate seed IDs")

    imported = {
        candidate_id
        for candidate_id, row in audit.items()
        if clean(row.get("pre_import_decision")) == "import_now"
    }
    if imported != {"E0-D001", "E0R1-C002"}:
        raise QueueBuildError(
            "The legacy import boundary changed; review imported IDs explicitly"
        )

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = clean(candidate.get("candidate_id"))
        if not candidate_id or candidate_id in seen:
            raise QueueBuildError(f"Invalid or duplicate candidate ID: {candidate_id!r}")
        seen.add(candidate_id)
        if candidate_id in imported:
            continue
        audit_row = audit.get(candidate_id)
        row = base_row(candidate_id)
        row.update(
            {
                "title": clean(candidate.get("title")),
                "doi": normalise_doi(candidate.get("doi")),
                "authors": clean(candidate.get("authors")),
                "year": clean(candidate.get("year")),
                "venue": clean(candidate.get("venue")),
                "work_type": "unknown",
                "source": clean(candidate.get("source")),
                "source_links": "",
                "other_identifiers": "; ".join(
                    value
                    for value in (
                        clean(candidate.get("openalex_id")),
                        clean(candidate.get("semantic_scholar_id")),
                        clean(candidate.get("crossref_id")),
                    )
                    if value and value != normalise_doi(candidate.get("doi"))
                ),
                "source_query_id": clean(candidate.get("source_query_id")),
                "verification_status": "legacy_unverified",
                "metadata_confidence": clean(candidate.get("metadata_confidence")),
                "intake_assessment": "",
                "intake_reason": "",
                "possible_duplicate": "",
                "metadata_conflict": "",
                "required_human_action": "",
                "origin": "legacy_e0r1",
                "legacy_scope_fit": clean(candidate.get("scope_fit")),
                "legacy_recommendation": clean(
                    (audit_row or {}).get("pre_import_decision")
                    or candidate.get("final_recommendation")
                ),
                "legacy_reason": joined_reason(
                    candidate.get("review_reason"),
                    (audit_row or {}).get("pre_import_audit_note"),
                ),
                "legacy_priority": clean(candidate.get("priority_for_e0")),
                "review_stage": stage_for_candidate(candidate, audit_row),
                "provenance": (
                    "data/legacy/e0/candidate_outcomes.csv:"
                    f"{candidate_id}"
                ),
            }
        )
        result.append(row)

    for candidate_id, audit_row in audit.items():
        if not candidate_id.startswith("E0-D") or candidate_id in imported:
            continue
        if candidate_id in seen:
            raise QueueBuildError(f"Seed duplicated across legacy inputs: {candidate_id}")
        seen.add(candidate_id)
        if clean(audit_row.get("pre_import_decision")) != "hold_for_manual_review":
            raise QueueBuildError(f"Unexpected seed disposition: {candidate_id}")
        row = base_row(candidate_id)
        row.update(
            {
                "title": clean(audit_row.get("title")),
                "doi": normalise_doi(audit_row.get("doi")),
                "authors": clean(audit_row.get("authors")),
                "year": clean(audit_row.get("year")),
                "venue": clean(audit_row.get("venue")),
                "work_type": "unknown",
                "source": clean(audit_row.get("source_basis")),
                "source_links": "",
                "other_identifiers": "",
                "source_query_id": "",
                "verification_status": "legacy_unverified",
                "metadata_confidence": "",
                "intake_assessment": "",
                "intake_reason": "",
                "possible_duplicate": "",
                "metadata_conflict": "",
                "required_human_action": "",
                "origin": "legacy_e0_seed",
                "legacy_scope_fit": clean(audit_row.get("seed_status")),
                "legacy_recommendation": clean(
                    audit_row.get("pre_import_decision")
                ),
                "legacy_reason": joined_reason(
                    audit_row.get("reason_for_seed_inclusion"),
                    audit_row.get("pre_import_audit_note"),
                ),
                "legacy_priority": "",
                "review_stage": "manual_review",
                "provenance": (
                    "data/legacy/e0/promotion_audit.csv:"
                    f"{candidate_id}"
                ),
            }
        )
        result.append(row)

    result.sort(key=lambda row: row["candidate_id"])
    counts = Counter(row["review_stage"] for row in result)
    if dict(counts) != EXPECTED_STAGE_COUNTS:
        raise QueueBuildError(
            f"Unexpected review-stage counts: {dict(counts)}; "
            f"expected {EXPECTED_STAGE_COUNTS}"
        )
    if len(result) != 55:
        raise QueueBuildError(f"Expected 55 materialised candidates, found {len(result)}")
    return result


def render(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="Repository root"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output CSV; defaults to data/curation/review_queue.csv",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed queue differs from the deterministic build",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    output = args.output or root / "data" / "curation" / "review_queue.csv"
    expected_rows = materialise(root)
    rendered = render(expected_rows)
    if args.check:
        if not output.exists():
            raise SystemExit("[FAIL] review_queue.csv is missing")
        committed = read_rows(output)
        expected = {row["candidate_id"]: row for row in expected_rows}
        committed_by_id = {
            row.get("candidate_id", ""): row for row in committed
        }
        if len(committed_by_id) != len(committed):
            raise SystemExit("[FAIL] review_queue.csv contains duplicate candidate IDs")
        if set(expected) - set(committed_by_id):
            raise SystemExit("[FAIL] review_queue.csv legacy candidate inventory is stale")
        unexpected_legacy = {
            candidate_id
            for candidate_id, row in committed_by_id.items()
            if row.get("origin", "").startswith("legacy_")
            and candidate_id not in expected
        }
        if unexpected_legacy:
            raise SystemExit(
                "[FAIL] review_queue.csv contains unexpected legacy candidate(s): "
                + ", ".join(sorted(unexpected_legacy))
            )
        static_fields = [field for field in FIELDS if field not in MUTABLE_FIELDS]
        for candidate_id, baseline in expected.items():
            row = committed_by_id[candidate_id]
            if any(row.get(field, "") != baseline[field] for field in static_fields):
                raise SystemExit(
                    "[FAIL] review_queue.csv changed legacy provenance for "
                    f"{candidate_id}"
                )
        print("[OK] Legacy curator queue provenance is deterministic: 55 candidates.")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"[OK] Wrote 55 candidates to {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, QueueBuildError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
