#!/usr/bin/env python3
"""Validate canonical registries and the generated public archive."""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/registry"
PUBLIC_ARCHIVE = ROOT / "site/data/archive.json"

ALLOWED_CANONICAL_STATUSES = {"seed_included", "review_included", "superseded"}
ALLOWED_DECISIONS = {
    "eligible_core",
    "eligible_contextual",
    "maybe_full_text_needed",
    "not_eligible",
    "duplicate",
    "not_academic",
    "not_retrievable",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.I)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def read_csv(name: str) -> list[dict[str, str]]:
    path = DATA / name
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def normalise_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def require_unique(rows: list[dict[str, str]], field: str, label: str) -> None:
    values = [row.get(field, "").strip() for row in rows]
    blank = sum(not value for value in values)
    if blank:
        fail(f"{label}: {blank} row(s) have an empty {field}")
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        fail(f"{label}: duplicate {field}: {', '.join(duplicates)}")


def validate_registries() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    papers = read_csv("papers.csv")
    events = read_csv("discovery_events.csv")
    decisions = read_csv("screening_decisions.csv")
    codes = read_csv("paper_codes.csv")

    if not papers:
        fail("Canonical papers registry is empty")
    require_unique(papers, "paper_id", "papers.csv")
    require_unique(events, "event_id", "discovery_events.csv")
    require_unique(decisions, "decision_id", "screening_decisions.csv")

    paper_ids = {row["paper_id"] for row in papers}
    for row in papers:
        missing = [
            field
            for field in ("title", "authors", "year", "venue", "canonical_status")
            if not row.get(field, "").strip()
        ]
        if missing:
            fail(f"{row['paper_id']}: missing required field(s): {', '.join(missing)}")
        if not re.fullmatch(r"\d{4}", row["year"].strip()):
            fail(f"{row['paper_id']}: invalid year {row['year']!r}")
        if row["canonical_status"] not in ALLOWED_CANONICAL_STATUSES:
            fail(
                f"{row['paper_id']}: invalid canonical_status "
                f"{row['canonical_status']!r}"
            )
        doi = row.get("doi", "").strip()
        if doi and not DOI_PATTERN.match(doi):
            fail(f"{row['paper_id']}: invalid DOI {doi!r}")

    dois = [row["doi"].strip().lower() for row in papers if row.get("doi", "").strip()]
    duplicate_dois = sorted(doi for doi, count in Counter(dois).items() if count > 1)
    if duplicate_dois:
        fail(f"Duplicate canonical DOI(s): {', '.join(duplicate_dois)}")

    title_year = [
        (normalise_title(row["title"]), row["year"].strip()) for row in papers
    ]
    duplicate_works = sorted(
        f"{title} ({year})"
        for (title, year), count in Counter(title_year).items()
        if count > 1
    )
    if duplicate_works:
        fail(f"Probable duplicate canonical work(s): {', '.join(duplicate_works)}")

    event_counts: Counter[str] = Counter()
    for row in events:
        if row.get("paper_id") not in paper_ids:
            fail(f"{row['event_id']}: orphan paper_id {row.get('paper_id')!r}")
        event_counts[row["paper_id"]] += 1

    current_decisions: Counter[str] = Counter()
    for row in decisions:
        paper_id = row.get("paper_id", "")
        if paper_id not in paper_ids:
            fail(f"{row['decision_id']}: orphan paper_id {paper_id!r}")
        if row.get("decision") not in ALLOWED_DECISIONS:
            fail(f"{row['decision_id']}: invalid decision {row.get('decision')!r}")
        if row.get("confidence") not in ALLOWED_CONFIDENCE:
            fail(f"{row['decision_id']}: invalid confidence {row.get('confidence')!r}")
        is_current = row.get("is_current", "").strip().lower()
        if is_current not in {"true", "false"}:
            fail(f"{row['decision_id']}: is_current must be true or false")
        if is_current == "true":
            current_decisions[paper_id] += 1
        if row.get("decision") in {"not_eligible", "duplicate", "not_academic", "not_retrievable"}:
            if not row.get("exclusion_reason_code", "").strip():
                fail(f"{row['decision_id']}: exclusion decision requires a reason code")

    for row in papers:
        paper_id = row["paper_id"]
        if row["canonical_status"] in {"seed_included", "review_included"}:
            if event_counts[paper_id] < 1:
                fail(f"{paper_id}: included record has no discovery event")
            if current_decisions[paper_id] != 1:
                fail(
                    f"{paper_id}: included record must have exactly one current "
                    f"screening decision; found {current_decisions[paper_id]}"
                )

    for row in codes:
        if row.get("paper_id") not in paper_ids:
            fail(f"paper_codes.csv: orphan paper_id {row.get('paper_id')!r}")
        if not row.get("dimension", "").strip() or not row.get("code", "").strip():
            fail("paper_codes.csv: every row requires dimension and code")

    return papers, decisions


def validate_public_archive(
    papers: list[dict[str, str]], decisions: list[dict[str, str]]
) -> None:
    if not PUBLIC_ARCHIVE.exists():
        fail("Generated archive is missing; run scripts/build_archive.py")
    payload = json.loads(PUBLIC_ARCHIVE.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        fail("archive.json records must be a list")

    included_ids = {
        row["paper_id"]
        for row in papers
        if row.get("canonical_status") in {"seed_included", "review_included"}
    }
    public_ids = {record.get("id") for record in records}
    if public_ids != included_ids:
        fail(
            "Public archive IDs do not match included canonical records: "
            f"expected {sorted(included_ids)}, got {sorted(public_ids)}"
        )

    forbidden_fields = {
        "reviewer",
        "evidence_quote",
        "exclusion_comment",
        "auditNote",
        "query_string",
    }
    for record in records:
        if record.get("section") != "included" or record.get("status") != "included":
            fail(f"{record.get('id')}: non-included record leaked into public archive")
        leaked = sorted(forbidden_fields.intersection(record))
        if leaked:
            fail(f"{record.get('id')}: internal field(s) leaked: {', '.join(leaked)}")
        if not record.get("reason"):
            fail(f"{record.get('id')}: missing public relevance reason")

    counts = payload.get("counts", {})
    if counts.get("records") != len(records) or counts.get("included") != len(records):
        fail("archive.json count metadata does not match records")


def main() -> None:
    papers, decisions = validate_registries()
    validate_public_archive(papers, decisions)
    print(
        f"[OK] Archive validation passed: {len(papers)} canonical record(s), "
        f"{len(decisions)} screening decision(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (csv.Error, json.JSONDecodeError, OSError) as exc:
        fail(str(exc))
