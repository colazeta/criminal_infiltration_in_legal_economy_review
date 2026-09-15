#!/usr/bin/env python3
"""Resolve reviewed stale candidate identity blockers from persisted evidence.

This is a metadata-verifier operation. It does not screen a paper, merge two
CandidateRecords, decide canonical ScholarlyWork identity, or publish a scientific
classification. It only applies an explicit reviewed declaration when the current
queue blocker and persisted retrieval evidence still match the declaration.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LEDGER = Path("data/curation/verified_identity_resolutions.json")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
ALLOWED_RESOLUTIONS = {"same_work_manifestation", "not_duplicate"}


class IdentityResolutionError(ValueError):
    """Raised when a reviewed identity resolution is stale or unsafe."""


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
            raise IdentityResolutionError(f"{path} has no header")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_ledger(root: Path) -> list[dict[str, Any]]:
    path = root / LEDGER
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityResolutionError(f"invalid identity-resolution ledger: {exc}") from exc
    if payload.get("schemaVersion") != 1 or not isinstance(payload.get("resolutions"), list):
        raise IdentityResolutionError("identity-resolution ledger has invalid schema")

    seen: set[str] = set()
    resolutions: list[dict[str, Any]] = []
    for raw in payload["resolutions"]:
        if not isinstance(raw, dict):
            raise IdentityResolutionError("identity-resolution entry is not an object")
        candidate_id = clean(raw.get("candidate_id"))
        if not candidate_id or candidate_id in seen:
            raise IdentityResolutionError("blank or duplicate identity-resolution candidate")
        seen.add(candidate_id)
        resolution = clean(raw.get("resolution"))
        if resolution not in ALLOWED_RESOLUTIONS:
            raise IdentityResolutionError(f"unsupported identity resolution: {candidate_id}")
        expected_hash = clean(raw.get("expected_possible_duplicate_sha256"))
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise IdentityResolutionError(f"invalid blocker hash: {candidate_id}")
        checked_at = clean(raw.get("checked_at"))
        try:
            checked_at = date.fromisoformat(checked_at).isoformat()
        except ValueError as exc:
            raise IdentityResolutionError(f"invalid checked_at: {candidate_id}") from exc
        evidence_sources = raw.get("evidence_sources")
        evidence_methods = raw.get("evidence_methods")
        if not isinstance(evidence_sources, list) or not all(clean(x) for x in evidence_sources):
            raise IdentityResolutionError(f"invalid evidence_sources: {candidate_id}")
        if not isinstance(evidence_methods, list) or not all(clean(x) for x in evidence_methods):
            raise IdentityResolutionError(f"invalid evidence_methods: {candidate_id}")
        if not clean(raw.get("basis")):
            raise IdentityResolutionError(f"missing basis: {candidate_id}")
        resolved_doi = normalise_doi(raw.get("resolved_doi"))
        if resolved_doi and not DOI_RE.fullmatch(resolved_doi):
            raise IdentityResolutionError(f"invalid resolved DOI: {candidate_id}")
        resolutions.append(
            {
                "candidate_id": candidate_id,
                "resolution": resolution,
                "expected_possible_duplicate_sha256": expected_hash,
                "resolved_doi": resolved_doi,
                "evidence_sources": [clean(x) for x in evidence_sources],
                "evidence_methods": [clean(x) for x in evidence_methods],
                "checked_at": checked_at,
                "basis": clean(raw.get("basis")),
            }
        )
    return resolutions


def index_rows(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = clean(row.get("candidate_id"))
        if not candidate_id or candidate_id in index:
            raise IdentityResolutionError(f"blank or duplicate candidate in {label}")
        index[candidate_id] = row
    return index


def validate_resolution(
    declaration: dict[str, Any],
    queue_row: dict[str, str],
    retrieval_row: dict[str, str],
) -> dict[str, str]:
    candidate_id = declaration["candidate_id"]
    if clean(queue_row.get("origin")) != "daily_surveillance":
        raise IdentityResolutionError(f"resolution candidate is not surveillance-origin: {candidate_id}")
    if clean(queue_row.get("current_status")) != "pending" or clean(queue_row.get("current_decision")):
        raise IdentityResolutionError(f"resolution candidate already has a scientific decision: {candidate_id}")
    if clean(queue_row.get("review_stage")) != "metadata_fix":
        raise IdentityResolutionError(f"resolution candidate is not at metadata_fix: {candidate_id}")
    if clean(queue_row.get("verification_status")) != "metadata_partial":
        raise IdentityResolutionError(f"resolution candidate is not metadata_partial: {candidate_id}")
    if clean(queue_row.get("metadata_conflict")):
        raise IdentityResolutionError(f"metadata conflict requires separate review: {candidate_id}")

    blocker = clean(queue_row.get("possible_duplicate"))
    if not blocker:
        return {"candidate_id": candidate_id, "status": "already_applied"}
    if sha256_text(blocker) != declaration["expected_possible_duplicate_sha256"]:
        raise IdentityResolutionError(f"possible_duplicate blocker changed since review: {candidate_id}")
    if normalise_title(queue_row.get("title")) != normalise_title(retrieval_row.get("title")):
        raise IdentityResolutionError(f"queue/retrieval title mismatch: {candidate_id}")
    if clean(retrieval_row.get("match_confidence")) != "high":
        raise IdentityResolutionError(f"identity resolution is not high confidence: {candidate_id}")

    sources = set(split_semicolon(retrieval_row.get("resolution_sources")))
    methods = set(split_semicolon(retrieval_row.get("match_method")))
    if not set(declaration["evidence_sources"]).issubset(sources):
        raise IdentityResolutionError(f"declared evidence source is absent from persisted retrieval: {candidate_id}")
    if not set(declaration["evidence_methods"]).issubset(methods):
        raise IdentityResolutionError(f"declared evidence method is absent from persisted retrieval: {candidate_id}")
    if not {"OpenAlex", "Crossref"}.issubset(sources):
        raise IdentityResolutionError(f"dual-source identity evidence is absent: {candidate_id}")
    if not {"OpenAlex:title_year", "Crossref:title_year"}.issubset(methods):
        raise IdentityResolutionError(f"dual title/year evidence is absent: {candidate_id}")

    declared_doi = declaration["resolved_doi"]
    persisted_doi = normalise_doi(retrieval_row.get("resolved_doi"))
    if declared_doi and declared_doi != persisted_doi:
        raise IdentityResolutionError(f"declared DOI disagrees with persisted retrieval: {candidate_id}")
    if declared_doi:
        doi_url = clean(retrieval_row.get("doi_url"))
        if doi_url.lower() != f"https://doi.org/{declared_doi}".lower():
            raise IdentityResolutionError(f"persisted DOI URL disagrees: {candidate_id}")
    if clean(queue_row.get("doi")) and normalise_doi(queue_row.get("doi")) != declared_doi:
        raise IdentityResolutionError(f"existing queue DOI disagrees with reviewed identity: {candidate_id}")

    return {"candidate_id": candidate_id, "status": "apply", "doi": declared_doi}


def resolve(root: Path, updated_at: str, *, check: bool = False) -> dict[str, Any]:
    updated_at = date.fromisoformat(updated_at).isoformat()
    queue_path = root / "data/curation/review_queue.csv"
    retrieval_path = root / "data/curation/retrieval_coverage.csv"
    fields, queue_rows = read_csv(queue_path)
    _, retrieval_rows = read_csv(retrieval_path)
    queue = index_rows(queue_rows, "review queue")
    retrieval = index_rows(retrieval_rows, "retrieval coverage")
    declarations = load_ledger(root)

    required = {
        "candidate_id",
        "title",
        "doi",
        "source_links",
        "verification_status",
        "metadata_confidence",
        "possible_duplicate",
        "metadata_conflict",
        "origin",
        "review_stage",
        "current_status",
        "current_decision",
        "updated_at",
    }
    missing = required - set(fields)
    if missing:
        raise IdentityResolutionError("review queue missing field(s): " + ", ".join(sorted(missing)))

    applicable: list[dict[str, str]] = []
    already_applied: list[str] = []
    for declaration in declarations:
        candidate_id = declaration["candidate_id"]
        if candidate_id not in queue or candidate_id not in retrieval:
            raise IdentityResolutionError(f"resolution candidate missing from governed data: {candidate_id}")
        result = validate_resolution(declaration, queue[candidate_id], retrieval[candidate_id])
        if result["status"] == "already_applied":
            already_applied.append(candidate_id)
        else:
            applicable.append({**result, "resolution": declaration["resolution"], "checked_at": declaration["checked_at"]})

    summary = {
        "schema_version": 1,
        "safe_identity_resolutions": len(applicable),
        "candidate_ids": [item["candidate_id"] for item in applicable],
        "already_applied": already_applied,
        "resolutions": applicable,
        "scientific_decisions_changed": 0,
        "canonical_records_changed": 0,
        "publication_records_changed": 0,
    }
    if check:
        if applicable:
            raise IdentityResolutionError(
                "reviewed identity resolution(s) remain unapplied: " + ", ".join(summary["candidate_ids"])
            )
        return summary

    by_id = {item["candidate_id"]: item for item in applicable}
    if by_id:
        for row in queue_rows:
            item = by_id.get(clean(row.get("candidate_id")))
            if item is None:
                continue
            row["possible_duplicate"] = ""
            if item.get("doi"):
                row["doi"] = item["doi"]
                doi_url = f"https://doi.org/{item['doi']}"
                links = split_semicolon(row.get("source_links"))
                if doi_url not in links:
                    links.append(doi_url)
                row["source_links"] = "; ".join(links)
            row["verification_status"] = "metadata_verified"
            row["metadata_confidence"] = "high"
            row["review_stage"] = "abstract_full_text_review"
            row["updated_at"] = updated_at
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
    summary = resolve(args.root.resolve(), args.updated_at, check=args.check)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, csv.Error, IdentityResolutionError) as exc:
        raise SystemExit(f"[IDENTITY RESOLUTION BLOCKED] {exc}") from exc
