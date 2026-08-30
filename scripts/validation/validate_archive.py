#!/usr/bin/env python3
"""Validate registry integrity and the generated public archive."""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_archive import (  # noqa: E402
    ELIGIBLE_DECISIONS,
    INCLUDED_STATUSES,
    PUBLIC_RECORD_FIELDS,
    ArchiveBuildError,
    build_payload,
    clean_doi,
    current_publication_rows,
)


REGISTRY = ROOT / "data/registry"
PUBLIC_JSON = ROOT / "site/data/archive.json"
PUBLIC_CSV = ROOT / "site/data/archive.csv"
PUBLIC_SCHEMA = ROOT / "schema/public-archive.schema.json"
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ALLOWED_CANONICAL_STATUSES = {
    *INCLUDED_STATUSES,
    "review_pending",
    "superseded",
    "withdrawn",
}
ALLOWED_DECISIONS = {
    *ELIGIBLE_DECISIONS,
    "maybe_full_text_needed",
    "not_eligible",
    "duplicate",
    "not_academic",
    "not_retrievable",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_PUBLICATION_STATUS = {"published", "withheld"}


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def rows(name: str) -> list[dict[str, str]]:
    with (REGISTRY / name).open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def require_unique(values: list[str], label: str) -> None:
    if any(not value for value in values):
        fail(f"{label}: blank identifier")
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        fail(f"{label}: duplicate value(s): {', '.join(duplicates)}")


def normalise_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def validate_registries() -> dict[str, list[dict[str, str]]]:
    data = {
        name: rows(name)
        for name in (
            "papers.csv",
            "work_identifiers.csv",
            "discovery_events.csv",
            "screening_decisions.csv",
            "publications.csv",
            "paper_codes.csv",
            "taxonomy.csv",
            "editorial_summary.csv",
            "archive_versions.csv",
            "execution_metrics.csv",
        )
    }
    papers = data["papers.csv"]
    identifiers = data["work_identifiers.csv"]
    events = data["discovery_events.csv"]
    decisions = data["screening_decisions.csv"]
    publications = data["publications.csv"]
    taxonomy = data["taxonomy.csv"]

    if not papers:
        fail("papers.csv is empty")
    require_unique([row.get("paper_id", "").strip() for row in papers], "papers.csv")
    require_unique(
        [row.get("identifier_id", "").strip() for row in identifiers],
        "work_identifiers.csv",
    )
    require_unique([row.get("event_id", "").strip() for row in events], "events")
    require_unique(
        [row.get("decision_id", "").strip() for row in decisions], "decisions"
    )
    require_unique(
        [row.get("publication_id", "").strip() for row in publications],
        "publications",
    )

    try:
        current_publications = current_publication_rows(publications)
    except ArchiveBuildError as exc:
        fail(f"Invalid publication history: {exc}")
    current_publication_by_paper = {
        row["paper_id"]: row for row in current_publications
    }

    paper_ids = {row["paper_id"] for row in papers}
    title_year: Counter[tuple[str, str]] = Counter()
    for row in papers:
        paper_id = row["paper_id"]
        for field in ("title", "authors", "year", "venue", "document_type"):
            if not row.get(field, "").strip():
                fail(f"{paper_id}: missing {field}")
        if not re.fullmatch(r"\d{4}", row["year"].strip()):
            fail(f"{paper_id}: invalid year")
        if row.get("canonical_status") not in ALLOWED_CANONICAL_STATUSES:
            fail(f"{paper_id}: invalid canonical status")
        if row.get("updated_at") and not DATE_PATTERN.match(row["updated_at"]):
            fail(f"{paper_id}: invalid updated_at")
        doi = clean_doi(row.get("doi", ""))
        if doi and not DOI_PATTERN.match(doi):
            fail(f"{paper_id}: invalid DOI")
        title_year[(normalise_title(row["title"]), row["year"])] += 1
    duplicates = [key for key, count in title_year.items() if count > 1]
    if duplicates:
        fail(f"Probable duplicate work(s): {duplicates}")

    identifier_keys: list[str] = []
    primary_doi_counts: Counter[str] = Counter()
    primary_doi_by_paper: dict[str, str] = {}
    for row in identifiers:
        paper_id = row.get("paper_id", "")
        if paper_id not in paper_ids:
            fail(f"{row.get('identifier_id')}: orphan paper_id")
        scheme = row.get("scheme", "").strip().lower()
        value = (
            clean_doi(row.get("value", ""))
            if scheme == "doi"
            else row.get("value", "").strip()
        )
        if not scheme or not value:
            fail(f"{row.get('identifier_id')}: blank identifier value")
        if scheme == "doi" and not DOI_PATTERN.match(value):
            fail(f"{row.get('identifier_id')}: invalid DOI")
        identifier_keys.append(f"{scheme}:{value.lower()}")
        is_primary = row.get("is_primary", "").strip().lower()
        if is_primary not in {"true", "false"}:
            fail(f"{row.get('identifier_id')}: invalid is_primary")
        if is_primary == "true" and scheme == "doi":
            primary_doi_counts[paper_id] += 1
            primary_doi_by_paper[paper_id] = value
        if row.get("verification_status") != "verified":
            fail(f"{row.get('identifier_id')}: identifier is not verified")
    require_unique(identifier_keys, "work identifiers")

    event_counts: Counter[str] = Counter()
    for row in events:
        paper_id = row.get("paper_id", "")
        if paper_id not in paper_ids:
            fail(f"{row.get('event_id')}: orphan paper_id")
        if row.get("retrieval_status") not in {"success", "partial", "failed"}:
            fail(f"{row.get('event_id')}: invalid retrieval_status")
        if not DATE_PATTERN.match(row.get("retrieved_at", "")):
            fail(f"{row.get('event_id')}: invalid retrieved_at")
        event_counts[paper_id] += 1

    current: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in decisions:
        paper_id = row.get("paper_id", "")
        if paper_id not in paper_ids:
            fail(f"{row.get('decision_id')}: orphan paper_id")
        if row.get("decision") not in ALLOWED_DECISIONS:
            fail(f"{row.get('decision_id')}: invalid decision")
        if row.get("confidence") not in ALLOWED_CONFIDENCE:
            fail(f"{row.get('decision_id')}: invalid confidence")
        if not DATE_PATTERN.match(row.get("decision_date", "")):
            fail(f"{row.get('decision_id')}: invalid decision_date")
        is_current = row.get("is_current", "").strip().lower()
        if is_current not in {"true", "false"}:
            fail(f"{row.get('decision_id')}: invalid is_current")
        if is_current == "true":
            current[paper_id].append(row)
        if row.get("decision") in {
            "not_eligible",
            "duplicate",
            "not_academic",
            "not_retrievable",
        } and not row.get("exclusion_reason_code", "").strip():
            fail(f"{row.get('decision_id')}: exclusion requires reason code")

    taxonomy_keys = {
        (row.get("dimension", "").strip(), row.get("code", "").strip())
        for row in taxonomy
    }
    if len(taxonomy_keys) != len(taxonomy) or any(
        not all(key) for key in taxonomy_keys
    ):
        fail("taxonomy.csv has blank or duplicate keys")

    publications_by_paper: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in publications:
        publication_id = row["publication_id"]
        paper_id = row["paper_id"]
        if paper_id not in paper_ids:
            fail(f"{publication_id}: orphan paper_id {paper_id}")
        publications_by_paper[paper_id].append(row)
        if row.get("publication_status") not in ALLOWED_PUBLICATION_STATUS:
            fail(f"{publication_id}: invalid publication status")
        if not row.get("version_note", "").strip():
            fail(f"{publication_id}: blank version_note")
        if not DATE_PATTERN.match(row.get("updated_at", "")):
            fail(f"{publication_id}: invalid updated_at")
        metadata_verified_at = row.get("metadata_verified_at", "").strip()
        if metadata_verified_at and not DATE_PATTERN.match(metadata_verified_at):
            fail(f"{publication_id}: invalid metadata_verified_at")
        first_published_version = row.get("first_published_version", "").strip()
        if first_published_version and not re.fullmatch(
            r"\d+\.\d+\.\d+", first_published_version
        ):
            fail(f"{publication_id}: invalid first_published_version")
        if row.get("publication_status") == "published":
            if ("topic", row.get("topic_code", "")) not in taxonomy_keys:
                fail(f"{publication_id}: unknown public topic")
            for field in (
                "public_relevance_reason",
                "scope_fit",
                "metadata_confidence",
                "source_basis",
                "metadata_verified_at",
                "first_published_version",
            ):
                if not row.get(field, "").strip():
                    fail(f"{publication_id}: blank {field}")
            if row.get("metadata_confidence") not in ALLOWED_CONFIDENCE:
                fail(f"{publication_id}: invalid metadata_confidence")

    for paper_id, history in publications_by_paper.items():
        ordered = sorted(history, key=lambda row: int(row["publication_version"]))
        previous_date = ""
        first_published_revision: int | None = None
        first_published_release = ""
        for row in ordered:
            updated_at = row["updated_at"]
            if previous_date and updated_at < previous_date:
                fail(f"{paper_id}: publication updated_at precedes its predecessor")
            previous_date = updated_at
            if (
                first_published_revision is None
                and row.get("publication_status") == "published"
            ):
                first_published_revision = int(row["publication_version"])
                first_published_release = row.get("first_published_version", "").strip()
            if (
                first_published_revision is not None
                and int(row["publication_version"]) >= first_published_revision
                and row.get("first_published_version", "").strip()
                != first_published_release
            ):
                fail(f"{paper_id}: first_published_version changed across history")

    for paper_id, publication in current_publication_by_paper.items():
        if len(current[paper_id]) != 1:
            fail(f"{paper_id}: current publication requires one current decision")
        if publication.get("publication_status") != "published":
            continue
        if event_counts[paper_id] < 1:
            fail(f"{paper_id}: published work has no discovery event")
        if current[paper_id][0].get("decision") not in ELIGIBLE_DECISIONS:
            fail(f"{paper_id}: published work is not currently eligible")
        if primary_doi_counts[paper_id] != 1:
            fail(f"{paper_id}: expected one primary DOI")
        paper = next(item for item in papers if item["paper_id"] == paper_id)
        if clean_doi(paper.get("doi", "")) != primary_doi_by_paper[paper_id]:
            fail(f"{paper_id}: primary DOI mismatch")

    for paper in papers:
        paper_id = paper["paper_id"]
        if paper.get("canonical_status") in INCLUDED_STATUSES:
            if len(current[paper_id]) != 1:
                fail(f"{paper_id}: included work must have one current decision")
            if paper_id not in current_publication_by_paper:
                fail(f"{paper_id}: included work lacks a publication-manifest row")

    for row in data["paper_codes.csv"]:
        if row.get("paper_id") not in paper_ids:
            fail("paper_codes.csv contains an orphan paper_id")
        if (row.get("dimension", ""), row.get("code", "")) not in taxonomy_keys:
            fail("paper_codes.csv contains a code outside taxonomy.csv")

    for name in ("editorial_summary.csv", "archive_versions.csv"):
        current_rows = [
            row
            for row in data[name]
            if row.get("is_current", "").strip().lower() == "true"
        ]
        if len(current_rows) != 1:
            fail(f"{name}: expected exactly one current row")

    try:
        build_payload(ROOT)
    except ArchiveBuildError as exc:
        fail(f"Publication gate failed: {exc}")
    return data


def validate_public_archive(data: dict[str, list[dict[str, str]]]) -> None:
    if not PUBLIC_JSON.exists() or not PUBLIC_CSV.exists():
        fail("Generated archive files are missing")
    payload = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
    schema = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
    if set(payload) != set(schema.get("required", [])):
        fail("archive.json top-level field allowlist differs from public schema")
    schema_record_fields = tuple(
        schema["properties"]["records"]["items"].get("required", [])
    )
    if schema_record_fields != PUBLIC_RECORD_FIELDS:
        fail("Machine-readable record schema differs from builder allowlist")
    records = payload.get("records")
    if not isinstance(records, list):
        fail("archive.json records must be a list")

    current_publications = current_publication_rows(data["publications.csv"])
    expected_ids = {
        row["paper_id"]
        for row in current_publications
        if row.get("publication_status") == "published"
    }
    public_ids = {record.get("id") for record in records}
    if public_ids != expected_ids:
        fail(f"Public IDs differ from publication manifest: {public_ids} != {expected_ids}")

    decision_by_id = {
        row["paper_id"]: row
        for row in data["screening_decisions.csv"]
        if row.get("is_current", "").lower() == "true"
    }
    for record in records:
        if tuple(record) != PUBLIC_RECORD_FIELDS:
            fail(f"{record.get('id')}: public field allowlist mismatch")
        if record.get("section") != "included" or record.get("status") != "included":
            fail(f"{record.get('id')}: non-included record leaked")
        if record.get("screeningDecision") != decision_by_id[record["id"]]["decision"]:
            fail(f"{record.get('id')}: exported decision is stale")
        doi = clean_doi(record.get("doi", ""))
        if record.get("links") != {"doi": f"https://doi.org/{doi}"}:
            fail(f"{record.get('id')}: unexpected public link")

    counts = payload.get("counts", {})
    if counts.get("records") != len(records) or counts.get("included") != len(records):
        fail("archive.json count metadata does not match records")

    with PUBLIC_CSV.open(newline="", encoding="utf-8-sig") as handle:
        csv_rows = list(csv.DictReader(handle))
    if [row.get("id") for row in csv_rows] != [record.get("id") for record in records]:
        fail("JSON/CSV record order differs")
    expected_csv_fields = [field for field in PUBLIC_RECORD_FIELDS if field != "links"]
    if csv_rows and list(csv_rows[0].keys()) != expected_csv_fields:
        fail("CSV public field allowlist mismatch")


def main() -> None:
    data = validate_registries()
    validate_public_archive(data)
    print(
        f"[OK] Archive gate passed: {len(data['papers.csv'])} canonical work(s), "
        f"{len(data['publications.csv'])} versioned publication row(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (csv.Error, json.JSONDecodeError, OSError, ValueError) as exc:
        fail(str(exc))
