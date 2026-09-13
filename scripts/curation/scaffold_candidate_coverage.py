#!/usr/bin/env python3
"""Keep candidate coverage projections structurally aligned with the curator queue.

Candidate preservation must not depend on network enrichment.  This module adds
only deterministic placeholder rows for newly materialised CandidateRecords and
preserves every existing enriched row byte-for-field.  Retrieval, abstract and
access workers may then replace the placeholders with stronger evidence later.

No eligibility, duplicate, canonical-identity or publication decision is made
here.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QUEUE_REL = Path("data/curation/review_queue.csv")

RETRIEVAL_REL = Path("data/curation/retrieval_coverage.csv")
ABSTRACT_REL = Path("data/curation/abstract_coverage.csv")
ACCESS_REL = Path("data/curation/access_coverage.csv")
COVERAGE_PATHS = (RETRIEVAL_REL, ABSTRACT_REL, ACCESS_REL)

RETRIEVAL_FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "resolution_status",
    "best_url",
    "best_url_kind",
    "full_text_url",
    "open_access_url",
    "landing_url",
    "doi_url",
    "source_urls",
    "resolved_doi",
    "resolution_sources",
    "match_method",
    "match_confidence",
    "checked_at",
    "notes",
]
ABSTRACT_FIELDS = [
    "candidate_id",
    "title",
    "doi",
    "coverage_status",
    "abstract_source",
    "article_url",
    "providers_tried",
    "match_type",
    "match_score",
    "provider_errors",
    "checked_at",
    "notes",
]
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

RETRIEVAL_PENDING_NOTE = (
    "Candidate-preservation placeholder; retrieval enrichment pending."
)
ABSTRACT_PENDING_NOTE = (
    "Candidate-preservation placeholder; abstract enrichment pending."
)
ACCESS_PENDING_NOTE = (
    "Candidate-preservation placeholder; access enrichment pending."
)


class CoverageScaffoldError(ValueError):
    """Raised when a projection cannot be reconciled without losing provenance."""


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _queue(root: Path) -> list[dict[str, str]]:
    fields, rows = _read_csv(root / QUEUE_REL)
    if not fields or "candidate_id" not in fields:
        raise CoverageScaffoldError("review_queue.csv is missing its governed header")
    ids = [row.get("candidate_id", "").strip() for row in rows]
    if any(not candidate_id for candidate_id in ids) or len(ids) != len(set(ids)):
        raise CoverageScaffoldError("review_queue.csv candidate IDs must be nonblank and unique")
    return rows


def _existing_index(
    root: Path,
    relative_path: Path,
    expected_fields: list[str],
    queue_ids: set[str],
) -> dict[str, dict[str, str]]:
    path = root / relative_path
    fields, rows = _read_csv(path)
    if fields and fields != expected_fields:
        raise CoverageScaffoldError(f"{relative_path}: governed header mismatch")
    if not fields and path.exists():
        raise CoverageScaffoldError(f"{relative_path}: empty or invalid governed header")

    result: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = row.get("candidate_id", "").strip()
        if not candidate_id:
            raise CoverageScaffoldError(f"{relative_path}: blank candidate_id")
        if candidate_id in result:
            raise CoverageScaffoldError(f"{relative_path}: duplicate candidate_id {candidate_id}")
        if candidate_id not in queue_ids:
            raise CoverageScaffoldError(
                f"{relative_path}: coverage row has no queue candidate: {candidate_id}"
            )
        result[candidate_id] = row
    return result


def _retrieval_placeholder(row: dict[str, str], checked_at: str) -> dict[str, str]:
    return {
        "candidate_id": row["candidate_id"],
        "title": row.get("title", ""),
        "doi": row.get("doi", ""),
        "resolution_status": "unresolved",
        "best_url": "",
        "best_url_kind": "none",
        "full_text_url": "",
        "open_access_url": "",
        "landing_url": "",
        "doi_url": "",
        "source_urls": "",
        "resolved_doi": "",
        "resolution_sources": "",
        "match_method": "preservation_pending",
        "match_confidence": "",
        "checked_at": checked_at,
        "notes": RETRIEVAL_PENDING_NOTE,
    }


def _abstract_placeholder(row: dict[str, str], checked_at: str) -> dict[str, str]:
    return {
        "candidate_id": row["candidate_id"],
        "title": row.get("title", ""),
        "doi": row.get("doi", ""),
        "coverage_status": "needs_web_search",
        "abstract_source": "",
        "article_url": "",
        "providers_tried": "",
        "match_type": "preservation_pending",
        "match_score": "",
        "provider_errors": "",
        "checked_at": checked_at,
        "notes": ABSTRACT_PENDING_NOTE,
    }


def _access_placeholder(row: dict[str, str], checked_at: str) -> dict[str, str]:
    return {
        "candidate_id": row["candidate_id"],
        "title": row.get("title", ""),
        "doi": row.get("doi", ""),
        "access_status": "unknown",
        "access_kind": "preservation_pending",
        "access_url": "",
        "evidence_source": "",
        "evidence_detail": "",
        "checked_at": checked_at,
        "notes": ACCESS_PENDING_NOTE,
    }


def _reconcile(
    root: Path,
    relative_path: Path,
    fields: list[str],
    queue_rows: list[dict[str, str]],
    checked_at: str,
    placeholder,
) -> int:
    queue_ids = {row["candidate_id"] for row in queue_rows}
    existing = _existing_index(root, relative_path, fields, queue_ids)
    output: list[dict[str, str]] = []
    added = 0
    for row in queue_rows:
        candidate_id = row["candidate_id"]
        if candidate_id in existing:
            output.append(existing[candidate_id])
        else:
            output.append(placeholder(row, checked_at))
            added += 1
    _write_csv(root / relative_path, fields, output)
    return added


def scaffold_all(root: Path = ROOT, checked_at: str | None = None) -> dict[str, int]:
    checked = date.fromisoformat(checked_at or date.today().isoformat()).isoformat()
    root = root.resolve()
    queue_rows = _queue(root)
    return {
        "retrieval": _reconcile(
            root,
            RETRIEVAL_REL,
            RETRIEVAL_FIELDS,
            queue_rows,
            checked,
            _retrieval_placeholder,
        ),
        "abstract": _reconcile(
            root,
            ABSTRACT_REL,
            ABSTRACT_FIELDS,
            queue_rows,
            checked,
            _abstract_placeholder,
        ),
        "access": _reconcile(
            root,
            ACCESS_REL,
            ACCESS_FIELDS,
            queue_rows,
            checked,
            _access_placeholder,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()
    try:
        result = scaffold_all(args.root, args.date)
    except (CoverageScaffoldError, ValueError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
    print(
        "[OK] Candidate coverage scaffolded: "
        f"retrieval={result['retrieval']}, abstract={result['abstract']}, "
        f"access={result['access']} placeholder row(s) added."
    )


if __name__ == "__main__":
    main()
