#!/usr/bin/env python3
"""Prepare conservative candidate metadata repairs from dual-source retrieval evidence.

This is a metadata-verifier step, not screening. It may repair a blank candidate
DOI and move the candidate out of the metadata-fix lane only when the persisted
retrieval ledger records concordant OpenAlex + Crossref title/year resolution,
with no candidate metadata conflict or duplicate flag. It never changes intake
assessment, screening decisions, canonical identity or publication state.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class MetadataReconciliationError(ValueError):
    """Raised when persisted evidence is structurally unsafe to reconcile."""


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalise_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", clean(value))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def normalise_doi(value: Any) -> str:
    doi = clean(value).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi.rstrip(" .")


def split_semicolon(value: Any) -> list[str]:
    return [item.strip() for item in clean(value).split(";") if item.strip()]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise MetadataReconciliationError(f"{path} has no header")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def retrieval_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = clean(row.get("candidate_id"))
        if not candidate_id:
            raise MetadataReconciliationError("retrieval row has no candidate_id")
        if candidate_id in index:
            raise MetadataReconciliationError(f"duplicate retrieval row: {candidate_id}")
        index[candidate_id] = row
    return index


def identity_repair_blockers(queue_row: dict[str, str], retrieval_row: dict[str, str]) -> list[str]:
    """Return explicit reasons why a persisted candidate cannot be mechanically repaired."""

    blockers: list[str] = []
    if clean(queue_row.get("origin")) != "daily_surveillance":
        blockers.append("not_daily_surveillance")
    if clean(queue_row.get("current_status")) != "pending":
        blockers.append("not_pending")
    if clean(queue_row.get("current_decision")):
        blockers.append("existing_decision")
    if clean(queue_row.get("verification_status")) != "metadata_partial":
        blockers.append("not_metadata_partial")
    if clean(queue_row.get("review_stage")) != "metadata_fix":
        blockers.append("not_metadata_fix")
    if clean(queue_row.get("doi")):
        blockers.append("doi_already_present")
    if clean(queue_row.get("metadata_conflict")):
        blockers.append("metadata_conflict")
    if clean(queue_row.get("possible_duplicate")):
        blockers.append("possible_duplicate")
    if normalise_title(queue_row.get("title")) != normalise_title(retrieval_row.get("title")):
        blockers.append("queue_retrieval_title_mismatch")

    confidence = clean(retrieval_row.get("match_confidence"))
    if confidence not in {"medium", "high"}:
        blockers.append("insufficient_match_confidence")

    sources = set(split_semicolon(retrieval_row.get("resolution_sources")))
    methods = set(split_semicolon(retrieval_row.get("match_method")))
    if not {"OpenAlex", "Crossref"}.issubset(sources):
        blockers.append("missing_dual_source")
    if not {"OpenAlex:title_year", "Crossref:title_year"}.issubset(methods):
        blockers.append("missing_dual_title_year_match")

    doi = normalise_doi(retrieval_row.get("resolved_doi"))
    if not DOI_RE.fullmatch(doi):
        blockers.append("invalid_resolved_doi")
    doi_url = clean(retrieval_row.get("doi_url"))
    if not doi or doi_url.lower() != f"https://doi.org/{doi}".lower():
        blockers.append("doi_url_disagreement")
    return blockers


def dual_source_identity_evidence(queue_row: dict[str, str], retrieval_row: dict[str, str]) -> tuple[str, str] | None:
    """Return (doi, doi_url) only for a deliberately narrow safe-repair case."""

    if identity_repair_blockers(queue_row, retrieval_row):
        return None
    doi = normalise_doi(retrieval_row.get("resolved_doi"))
    return doi, f"https://doi.org/{doi}"


def find_safe_repairs(
    queue_rows: list[dict[str, str]],
    retrieval_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    retrieval = retrieval_index(retrieval_rows)
    repairs: list[dict[str, str]] = []
    for row in queue_rows:
        candidate_id = clean(row.get("candidate_id"))
        evidence = retrieval.get(candidate_id)
        if evidence is None:
            continue
        resolved = dual_source_identity_evidence(row, evidence)
        if resolved is None:
            continue
        doi, doi_url = resolved
        repairs.append(
            {
                "candidate_id": candidate_id,
                "doi": doi,
                "doi_url": doi_url,
                "checked_at": clean(evidence.get("checked_at")),
                "resolution_sources": clean(evidence.get("resolution_sources")),
                "match_method": clean(evidence.get("match_method")),
                "match_confidence": clean(evidence.get("match_confidence")),
            }
        )
    return repairs


def apply_repairs(
    queue_rows: list[dict[str, str]],
    repairs: list[dict[str, str]],
    updated_at: str,
) -> None:
    repair_by_id = {repair["candidate_id"]: repair for repair in repairs}
    for row in queue_rows:
        repair = repair_by_id.get(clean(row.get("candidate_id")))
        if repair is None:
            continue
        row["doi"] = repair["doi"]
        links = split_semicolon(row.get("source_links"))
        if repair["doi_url"] not in links:
            links.append(repair["doi_url"])
        row["source_links"] = "; ".join(links)
        row["verification_status"] = "metadata_verified"
        row["metadata_confidence"] = "high"
        row["review_stage"] = "abstract_full_text_review"
        row["updated_at"] = updated_at


def reconcile(root: Path, updated_at: str, *, check: bool = False) -> dict[str, Any]:
    updated_at = date.fromisoformat(updated_at).isoformat()
    queue_path = root / "data" / "curation" / "review_queue.csv"
    retrieval_path = root / "data" / "curation" / "retrieval_coverage.csv"
    fields, queue_rows = read_csv(queue_path)
    _, retrieval_rows = read_csv(retrieval_path)

    required = {
        "candidate_id",
        "title",
        "doi",
        "source_links",
        "verification_status",
        "metadata_confidence",
        "metadata_conflict",
        "possible_duplicate",
        "origin",
        "review_stage",
        "current_status",
        "current_decision",
        "updated_at",
    }
    missing = required - set(fields)
    if missing:
        raise MetadataReconciliationError("review queue missing field(s): " + ", ".join(sorted(missing)))

    repairs = find_safe_repairs(queue_rows, retrieval_rows)
    summary = {
        "schema_version": 1,
        "safe_repairs": len(repairs),
        "candidate_ids": [repair["candidate_id"] for repair in repairs],
        "repairs": repairs,
        "scientific_decisions_changed": 0,
        "canonical_records_changed": 0,
        "publication_records_changed": 0,
    }
    if check:
        if repairs:
            raise MetadataReconciliationError(
                "safe candidate metadata repair(s) remain unapplied: "
                + ", ".join(summary["candidate_ids"])
            )
        return summary

    if repairs:
        apply_repairs(queue_rows, repairs, updated_at)
        write_csv(queue_path, fields, queue_rows)
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
    except (OSError, csv.Error, MetadataReconciliationError) as exc:
        raise SystemExit(f"[METADATA RECONCILIATION BLOCKED] {exc}") from exc
