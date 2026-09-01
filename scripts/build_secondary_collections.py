#!/usr/bin/env python3
"""Build public secondary collections from governed canonical registries only.

Secondary collections are deliberately separate from the systematic-review
archive. A published secondary record must be a canonical scholarly work with
an evidence-backed current ``not_eligible`` decision, an explicit collection
publication approval and a retained ``withheld`` state in the core manifest.
Candidate and curator-working files are never read.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from build_archive import clean_doi, normalise_title, source_snapshot, year_value


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "site/data"
SECONDARY_PUBLICATION_STATUSES = {"published", "withheld"}
SECONDARY_RECORD_FIELDS = (
    "id",
    "collectionCode",
    "collectionLabel",
    "section",
    "status",
    "statusLabel",
    "statusDescription",
    "title",
    "authors",
    "year",
    "venue",
    "publisher",
    "volume",
    "issue",
    "pages",
    "documentType",
    "language",
    "doi",
    "links",
    "exclusionReasonCode",
    "exclusionReasonLabel",
    "reason",
    "screeningDecision",
    "screeningStage",
    "metadataConfidence",
    "sourceBasis",
)


class SecondaryCollectionBuildError(ValueError):
    """Raised when a requested secondary record does not pass its gate."""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def registry_rows(root: Path, name: str) -> list[dict[str, str]]:
    return read_csv(root / "data/registry" / name)


def one_current(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if (row.get("is_current") or "").strip().lower() == "true":
            grouped[(row.get(key) or "").strip()].append(row)
    result: dict[str, dict[str, str]] = {}
    for item_id, current in grouped.items():
        if len(current) == 1:
            result[item_id] = current[0]
    return result


def current_secondary_publication_rows(
    publications: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Validate version chains and return one current row per work/collection."""

    by_id: dict[str, dict[str, str]] = {}
    by_membership: dict[tuple[str, str], dict[int, dict[str, str]]] = defaultdict(dict)
    for row in publications:
        publication_id = (row.get("secondary_publication_id") or "").strip()
        paper_id = (row.get("paper_id") or "").strip()
        collection_code = (row.get("collection_code") or "").strip()
        if not publication_id:
            raise SecondaryCollectionBuildError(
                "secondary_publications.csv: blank secondary_publication_id"
            )
        if publication_id in by_id:
            raise SecondaryCollectionBuildError(
                f"secondary_publications.csv: duplicate secondary_publication_id {publication_id}"
            )
        if not paper_id or not collection_code:
            raise SecondaryCollectionBuildError(
                f"{publication_id}: blank paper_id or collection_code"
            )
        try:
            version = int((row.get("publication_version") or "").strip())
        except ValueError as exc:
            raise SecondaryCollectionBuildError(
                f"{publication_id}: publication_version must be a positive integer"
            ) from exc
        if version < 1:
            raise SecondaryCollectionBuildError(
                f"{publication_id}: publication_version must be a positive integer"
            )
        key = (paper_id, collection_code)
        if version in by_membership[key]:
            raise SecondaryCollectionBuildError(
                f"{paper_id}/{collection_code}: duplicate publication_version {version}"
            )
        status = (row.get("publication_status") or "").strip()
        if status not in SECONDARY_PUBLICATION_STATUSES:
            raise SecondaryCollectionBuildError(
                f"{publication_id}: unknown publication status {status!r}"
            )
        is_current = (row.get("is_current") or "").strip().lower()
        if is_current not in {"true", "false"}:
            raise SecondaryCollectionBuildError(
                f"{publication_id}: is_current must be true or false"
            )
        by_id[publication_id] = row
        by_membership[key][version] = row

    current: list[dict[str, str]] = []
    for key, version_rows in by_membership.items():
        versions = sorted(version_rows)
        if versions != list(range(1, len(versions) + 1)):
            raise SecondaryCollectionBuildError(
                f"{key[0]}/{key[1]}: publication versions must be contiguous from 1; "
                f"found {versions}"
            )
        current_rows = [
            row
            for row in version_rows.values()
            if (row.get("is_current") or "").strip().lower() == "true"
        ]
        if len(current_rows) != 1:
            raise SecondaryCollectionBuildError(
                f"{key[0]}/{key[1]}: expected one current secondary publication row, "
                f"found {len(current_rows)}"
            )
        current_row = current_rows[0]
        if int(current_row["publication_version"]) != versions[-1]:
            raise SecondaryCollectionBuildError(
                f"{key[0]}/{key[1]}: current row must be the latest version"
            )
        for version in versions:
            row = version_rows[version]
            publication_id = row["secondary_publication_id"].strip()
            supersedes = (row.get("supersedes_secondary_publication_id") or "").strip()
            if version == 1:
                if supersedes:
                    raise SecondaryCollectionBuildError(
                        f"{publication_id}: version 1 cannot supersede another row"
                    )
                continue
            predecessor_id = version_rows[version - 1][
                "secondary_publication_id"
            ].strip()
            if supersedes != predecessor_id:
                raise SecondaryCollectionBuildError(
                    f"{publication_id}: supersedes_secondary_publication_id must "
                    f"reference {predecessor_id}"
                )
        current.append(current_row)
    return current


def current_core_publications(
    publications: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in publications:
        if (row.get("is_current") or "").strip().lower() == "true":
            grouped[(row.get("paper_id") or "").strip()].append(row)
    result: dict[str, dict[str, str]] = {}
    for paper_id, rows in grouped.items():
        if len(rows) == 1:
            result[paper_id] = rows[0]
    return result


def identifier_maps(
    identifiers: list[dict[str, str]],
) -> tuple[Counter[str], dict[str, str]]:
    primary_counts: Counter[str] = Counter()
    primary_doi: dict[str, str] = {}
    for row in identifiers:
        paper_id = (row.get("paper_id") or "").strip()
        if (
            (row.get("is_primary") or "").strip().lower() == "true"
            and (row.get("verification_status") or "").strip() == "verified"
        ):
            primary_counts[paper_id] += 1
            if (row.get("scheme") or "").strip().lower() == "doi":
                primary_doi[paper_id] = clean_doi(row.get("value", ""))
    return primary_counts, primary_doi


def build_records(
    papers: list[dict[str, str]],
    events: list[dict[str, str]],
    decisions: list[dict[str, str]],
    core_publications: list[dict[str, str]],
    identifiers: list[dict[str, str]],
    collections: list[dict[str, str]],
    secondary_publications: list[dict[str, str]],
    exclusion_reasons: list[dict[str, str]],
) -> list[dict[str, Any]]:
    papers_by_id = {(row.get("paper_id") or "").strip(): row for row in papers}
    if len(papers_by_id) != len(papers):
        raise SecondaryCollectionBuildError("Duplicate canonical paper_id")
    collection_by_code = {
        (row.get("collection_code") or "").strip(): row for row in collections
    }
    if len(collection_by_code) != len(collections) or "" in collection_by_code:
        raise SecondaryCollectionBuildError("Duplicate or blank secondary collection code")
    reason_labels = {
        (row.get("code") or "").strip(): (row.get("label") or "").strip()
        for row in exclusion_reasons
    }
    current_decisions = one_current(decisions, "paper_id")
    current_decision_counts = Counter(
        (row.get("paper_id") or "").strip()
        for row in decisions
        if (row.get("is_current") or "").strip().lower() == "true"
    )
    current_core = current_core_publications(core_publications)
    event_counts = Counter((row.get("paper_id") or "").strip() for row in events)
    primary_counts, primary_doi = identifier_maps(identifiers)

    records: list[dict[str, Any]] = []
    for publication in current_secondary_publication_rows(secondary_publications):
        if (publication.get("publication_status") or "").strip() != "published":
            continue
        paper_id = (publication.get("paper_id") or "").strip()
        collection_code = (publication.get("collection_code") or "").strip()
        paper = papers_by_id.get(paper_id)
        collection = collection_by_code.get(collection_code)
        decision = current_decisions.get(paper_id, {})
        reason_code = (decision.get("exclusion_reason_code") or "").strip()
        problems: list[str] = []
        if not paper:
            problems.append("missing canonical paper")
        else:
            if (paper.get("canonical_status") or "").strip() != "review_excluded":
                problems.append("canonical status is not review_excluded")
            for field in ("title", "authors", "year", "venue", "document_type"):
                if not (paper.get(field) or "").strip():
                    problems.append(f"missing bibliographic field {field}")
        if not collection:
            problems.append("unknown secondary collection")
        elif (collection.get("eligibility_relation") or "").strip() != "outside_core_review":
            problems.append("secondary collection does not preserve the core boundary")
        if event_counts[paper_id] < 1:
            problems.append("no discovery event")
        if current_decision_counts[paper_id] != 1:
            problems.append(
                f"expected one current decision, found {current_decision_counts[paper_id]}"
            )
        if (decision.get("decision") or "").strip() != "not_eligible":
            problems.append("current decision is not not_eligible")
        if reason_code not in reason_labels:
            problems.append("current exclusion reason is missing or uncontrolled")
        core_publication = current_core.get(paper_id)
        if not core_publication or (
            core_publication.get("publication_status") or ""
        ).strip() != "withheld":
            problems.append("core publication manifest is not withheld")
        for field in (
            "public_relevance_reason",
            "metadata_confidence",
            "source_basis",
            "metadata_verified_at",
        ):
            if not (publication.get(field) or "").strip():
                problems.append(f"missing approved public field {field}")
        if primary_counts[paper_id] < 1:
            problems.append("no verified primary identifier")
        doi = primary_doi.get(paper_id, "")
        if paper and clean_doi(paper.get("doi", "")) != doi:
            problems.append("papers.csv DOI and verified primary DOI disagree")
        if problems:
            raise SecondaryCollectionBuildError(
                f"{paper_id}/{collection_code}: " + "; ".join(problems)
            )

        assert paper is not None and collection is not None
        links = {"doi": f"https://doi.org/{doi}"} if doi else {}
        record = {
            "id": paper_id,
            "collectionCode": collection_code,
            "collectionLabel": (collection.get("label") or "").strip(),
            "section": "broader_aml",
            "status": "outside_core_review",
            "statusLabel": "Outside the core review",
            "statusDescription": (
                "Retained in the broader AML and economic/financial-crime collection; "
                "not included in the criminal-infiltration review corpus."
            ),
            "title": (paper.get("title") or "").strip(),
            "authors": (paper.get("authors") or "").strip(),
            "year": year_value(paper.get("year", "")),
            "venue": (paper.get("venue") or "").strip(),
            "publisher": (paper.get("publisher") or "").strip(),
            "volume": (paper.get("volume") or "").strip(),
            "issue": (paper.get("issue") or "").strip(),
            "pages": (paper.get("pages") or "").strip(),
            "documentType": (paper.get("document_type") or "").strip(),
            "language": (paper.get("language") or "").strip(),
            "doi": doi,
            "links": links,
            "exclusionReasonCode": reason_code,
            "exclusionReasonLabel": reason_labels[reason_code],
            "reason": (publication.get("public_relevance_reason") or "").strip(),
            "screeningDecision": "not_eligible",
            "screeningStage": (decision.get("screening_stage") or "").strip(),
            "metadataConfidence": (
                publication.get("metadata_confidence") or ""
            ).strip(),
            "sourceBasis": (publication.get("source_basis") or "").strip(),
        }
        if tuple(record) != SECONDARY_RECORD_FIELDS:
            raise SecondaryCollectionBuildError(
                "Internal secondary public record schema drift"
            )
        records.append(record)
    records.sort(
        key=lambda row: (
            row["collectionCode"],
            -(row["year"] or 0),
            normalise_title(row["title"]),
            row["id"],
        )
    )
    return records


def current_singleton(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    current = [
        row
        for row in rows
        if (row.get("is_current") or "").strip().lower() == "true"
    ]
    if len(current) != 1:
        raise SecondaryCollectionBuildError(
            f"{label}: expected one current row, found {len(current)}"
        )
    return current[0]


def build_payload(root: Path = ROOT) -> dict[str, Any]:
    papers = registry_rows(root, "papers.csv")
    events = registry_rows(root, "discovery_events.csv")
    decisions = registry_rows(root, "screening_decisions.csv")
    core_publications = registry_rows(root, "publications.csv")
    identifiers = registry_rows(root, "work_identifiers.csv")
    collections = registry_rows(root, "secondary_collections.csv")
    secondary_publications = registry_rows(root, "secondary_publications.csv")
    exclusion_reasons = registry_rows(root, "exclusion_reasons.csv")
    versions = registry_rows(root, "archive_versions.csv")
    version = current_singleton(versions, "archive_versions.csv")
    records = build_records(
        papers,
        events,
        decisions,
        core_publications,
        identifiers,
        collections,
        secondary_publications,
        exclusion_reasons,
    )
    counts = Counter(record["collectionCode"] for record in records)
    counts_by_collection = {
        row["collection_code"].strip(): counts[row["collection_code"].strip()]
        for row in sorted(collections, key=lambda item: item["collection_code"])
    }
    collection_payload = [
        {
            "code": row["collection_code"].strip(),
            "label": row["label"].strip(),
            "description": row["description"].strip(),
            "eligibilityRelation": row["eligibility_relation"].strip(),
            "records": counts[row["collection_code"].strip()],
        }
        for row in sorted(collections, key=lambda item: item["collection_code"])
    ]
    return {
        "schemaVersion": 1,
        "archiveVersion": version["version"],
        "releaseDate": version["release_date"],
        "searchCoverageThrough": version["search_coverage_through"],
        "sourceSnapshot": source_snapshot(
            [*papers, *decisions, *secondary_publications, version]
        ),
        "methodology": {
            "collectionDefinition": (
                "Secondary collections retain reviewed scholarly work that is useful "
                "outside the systematic review's narrower eligibility boundary."
            ),
            "coreBoundary": (
                "Every record here has a current not_eligible decision and remains "
                "withheld from the criminal-infiltration review corpus."
            ),
            "publicationDefinition": (
                "Visibility requires verified canonical metadata and a separate, "
                "versioned secondary-publication approval."
            ),
        },
        "counts": {
            "records": len(records),
            "byCollection": counts_by_collection,
        },
        "collections": collection_payload,
        "records": records,
    }


def write_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "secondary-collections.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    csv_fields = [field for field in SECONDARY_RECORD_FIELDS if field != "links"]
    with (output_dir / "secondary-collections.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=csv_fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for record in payload["records"]:
            safe = dict(record)
            for field in csv_fields:
                value = safe.get(field)
                if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                    safe[field] = "'" + value
            writer.writerow(safe)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory for secondary-collections.json and CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload()
    write_outputs(payload, args.output_dir)
    print(
        "Built public secondary collections: "
        f"{payload['counts']['records']} approved record(s)."
    )


if __name__ == "__main__":
    try:
        main()
    except (
        SecondaryCollectionBuildError,
        csv.Error,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
