#!/usr/bin/env python3
"""Build the public archive from governed registries only.

The builder is deliberately fail-closed. A row marked ``published`` in the
publication manifest is emitted only when the canonical work, discovery event,
current eligibility decision and approved public annotation all satisfy the
publication gate. Editorial and legacy files are never read.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "site/data"

INCLUDED_STATUSES = {"seed_included", "review_included"}
ELIGIBLE_DECISIONS = {"eligible_core", "eligible_contextual"}
PUBLICATION_STATUSES = {"published", "withheld"}

TOPIC_LABELS = {
    "conceptual_foundations": "Conceptual foundations",
    "criminal_transplantation": "Criminal transplantation",
}

PUBLIC_RECORD_FIELDS = (
    "id",
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
    "topicCode",
    "topicLabel",
    "scopeFit",
    "metadataConfidence",
    "reason",
    "screeningDecision",
    "screeningStage",
    "sourceBasis",
)


class ArchiveBuildError(ValueError):
    """Raised when a requested public record does not pass the gate."""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def registry_rows(root: Path, name: str) -> list[dict[str, str]]:
    return read_csv(root / "data/registry" / name)


def normalise_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def clean_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^(?:doi:)?\s*https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.rstrip(".,; ").lower()


def year_value(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def source_snapshot(rows: Iterable[dict[str, str]]) -> str:
    dates: list[str] = []
    for row in rows:
        for key in (
            "updated_at",
            "metadata_verified_at",
            "decision_date",
            "snapshot_date",
            "release_date",
        ):
            value = (row.get(key) or "").strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                dates.append(value)
    return max(dates, default="")


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


def current_publication_rows(
    publications: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Validate publication-version chains and return one current row per work."""

    by_id: dict[str, dict[str, str]] = {}
    by_paper: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for row in publications:
        publication_id = (row.get("publication_id") or "").strip()
        paper_id = (row.get("paper_id") or "").strip()
        if not publication_id:
            raise ArchiveBuildError("publications.csv: blank publication_id")
        if publication_id in by_id:
            raise ArchiveBuildError(
                f"publications.csv: duplicate publication_id {publication_id}"
            )
        if not paper_id:
            raise ArchiveBuildError(f"{publication_id}: blank paper_id")
        try:
            version = int((row.get("publication_version") or "").strip())
        except ValueError as exc:
            raise ArchiveBuildError(
                f"{publication_id}: publication_version must be a positive integer"
            ) from exc
        if version < 1:
            raise ArchiveBuildError(
                f"{publication_id}: publication_version must be a positive integer"
            )
        if version in by_paper[paper_id]:
            raise ArchiveBuildError(
                f"{paper_id}: duplicate publication_version {version}"
            )
        status = (row.get("publication_status") or "").strip()
        if status not in PUBLICATION_STATUSES:
            raise ArchiveBuildError(
                f"{publication_id}: unknown publication status {status!r}"
            )
        is_current = (row.get("is_current") or "").strip().lower()
        if is_current not in {"true", "false"}:
            raise ArchiveBuildError(
                f"{publication_id}: is_current must be true or false"
            )
        by_id[publication_id] = row
        by_paper[paper_id][version] = row

    current: list[dict[str, str]] = []
    for paper_id, version_rows in by_paper.items():
        versions = sorted(version_rows)
        expected = list(range(1, len(versions) + 1))
        if versions != expected:
            raise ArchiveBuildError(
                f"{paper_id}: publication versions must be contiguous from 1; "
                f"found {versions}"
            )
        current_rows = [
            row
            for row in version_rows.values()
            if (row.get("is_current") or "").strip().lower() == "true"
        ]
        if len(current_rows) != 1:
            raise ArchiveBuildError(
                f"{paper_id}: expected one current publication row, "
                f"found {len(current_rows)}"
            )
        current_row = current_rows[0]
        current_version = int(current_row["publication_version"])
        if current_version != versions[-1]:
            raise ArchiveBuildError(
                f"{paper_id}: current publication row must be the latest version"
            )

        for version in versions:
            row = version_rows[version]
            publication_id = (row.get("publication_id") or "").strip()
            supersedes = (row.get("supersedes_publication_id") or "").strip()
            if version == 1:
                if supersedes:
                    raise ArchiveBuildError(
                        f"{publication_id}: version 1 cannot supersede another row"
                    )
                continue
            predecessor = version_rows[version - 1]
            predecessor_id = (
                predecessor.get("publication_id") or ""
            ).strip()
            if supersedes != predecessor_id:
                raise ArchiveBuildError(
                    f"{publication_id}: supersedes_publication_id must reference "
                    f"the preceding version {predecessor_id}"
                )
        current.append(current_row)

    return current


def identifier_maps(
    identifiers: list[dict[str, str]],
) -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
    primary_doi: dict[str, str] = {}
    by_paper: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in identifiers:
        paper_id = (row.get("paper_id") or "").strip()
        by_paper[paper_id].append(row)
        if (
            (row.get("scheme") or "").strip().lower() == "doi"
            and (row.get("is_primary") or "").strip().lower() == "true"
            and (row.get("verification_status") or "").strip() == "verified"
        ):
            primary_doi[paper_id] = clean_doi(row.get("value", ""))
    return primary_doi, by_paper


def status_copy(canonical_status: str, decision: str) -> tuple[str, str]:
    tier = "Core" if decision == "eligible_core" else "Contextual"
    if canonical_status == "seed_included":
        return (
            f"{tier} seed",
            "Published seed record with a governed current eligibility decision. "
            "It contributes to the initial nucleus and does not imply review saturation.",
        )
    return (
        f"{tier} evidence",
        "Published record with a governed current eligibility decision in the living corpus.",
    )


def build_records(
    papers: list[dict[str, str]],
    events: list[dict[str, str]],
    decisions: list[dict[str, str]],
    publications: list[dict[str, str]],
    identifiers: list[dict[str, str]],
    topic_labels: dict[str, str],
) -> list[dict[str, Any]]:
    papers_by_id = {(row.get("paper_id") or "").strip(): row for row in papers}
    if len(papers_by_id) != len(papers):
        raise ArchiveBuildError("Duplicate canonical paper_id")
    current_by_id = one_current(decisions, "paper_id")
    current_counts = Counter(
        (row.get("paper_id") or "").strip()
        for row in decisions
        if (row.get("is_current") or "").strip().lower() == "true"
    )
    event_counts = Counter((row.get("paper_id") or "").strip() for row in events)
    primary_doi, identifiers_by_id = identifier_maps(identifiers)

    records: list[dict[str, Any]] = []
    for publication in current_publication_rows(publications):
        publication_status = (publication.get("publication_status") or "").strip()
        if publication_status != "published":
            continue

        paper_id = (publication.get("paper_id") or "").strip()
        paper = papers_by_id.get(paper_id)
        problems: list[str] = []
        if not paper:
            problems.append("missing canonical paper")
        else:
            if (paper.get("canonical_status") or "").strip() not in INCLUDED_STATUSES:
                problems.append("canonical status is not included")
            for field in ("title", "authors", "year", "venue", "document_type"):
                if not (paper.get(field) or "").strip():
                    problems.append(f"missing bibliographic field {field}")

        if event_counts[paper_id] < 1:
            problems.append("no discovery event")
        if current_counts[paper_id] != 1:
            problems.append(
                f"expected one current decision, found {current_counts[paper_id]}"
            )
        decision = current_by_id.get(paper_id, {})
        decision_value = (decision.get("decision") or "").strip()
        if decision_value not in ELIGIBLE_DECISIONS:
            problems.append("current decision is not eligible")
        for field in (
            "public_relevance_reason",
            "scope_fit",
            "metadata_confidence",
            "source_basis",
            "metadata_verified_at",
        ):
            if not (publication.get(field) or "").strip():
                problems.append(f"missing approved public field {field}")
        topic_code = (publication.get("topic_code") or "").strip()
        if topic_code not in topic_labels:
            problems.append("public topic is not in the controlled taxonomy")
        doi = primary_doi.get(paper_id, "")
        if not doi:
            problems.append("no verified primary DOI")
        if paper and clean_doi(paper.get("doi", "")) != doi:
            problems.append("papers.csv DOI and primary identifier disagree")
        if not identifiers_by_id.get(paper_id):
            problems.append("no identifier record")
        if problems:
            raise ArchiveBuildError(f"{paper_id}: " + "; ".join(problems))

        assert paper is not None
        status_label, status_description = status_copy(
            (paper.get("canonical_status") or "").strip(), decision_value
        )
        record = {
            "id": paper_id,
            "section": "included",
            "status": "included",
            "statusLabel": status_label,
            "statusDescription": status_description,
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
            "links": {"doi": f"https://doi.org/{doi}"},
            "topicCode": topic_code,
            "topicLabel": topic_labels[topic_code],
            "scopeFit": (publication.get("scope_fit") or "").strip(),
            "metadataConfidence": (
                publication.get("metadata_confidence") or ""
            ).strip(),
            "reason": (publication.get("public_relevance_reason") or "").strip(),
            "screeningDecision": decision_value,
            "screeningStage": (decision.get("screening_stage") or "").strip(),
            "sourceBasis": (publication.get("source_basis") or "").strip(),
        }
        if tuple(record) != PUBLIC_RECORD_FIELDS:
            raise ArchiveBuildError("Internal public record schema drift")
        records.append(record)

    records.sort(
        key=lambda row: (-(row["year"] or 0), normalise_title(row["title"]), row["id"])
    )
    return records


def current_singleton(rows: list[dict[str, str]], label: str) -> dict[str, str]:
    current = [
        row
        for row in rows
        if (row.get("is_current") or "").strip().lower() == "true"
    ]
    if len(current) != 1:
        raise ArchiveBuildError(f"{label}: expected one current row, found {len(current)}")
    return current[0]


def as_nonnegative_int(row: dict[str, str], field: str) -> int:
    try:
        value = int((row.get(field) or "").strip())
    except ValueError as exc:
        raise ArchiveBuildError(f"editorial_summary.csv: invalid {field}") from exc
    if value < 0:
        raise ArchiveBuildError(f"editorial_summary.csv: {field} cannot be negative")
    return value


def build_payload(root: Path = ROOT) -> dict[str, Any]:
    papers = registry_rows(root, "papers.csv")
    events = registry_rows(root, "discovery_events.csv")
    decisions = registry_rows(root, "screening_decisions.csv")
    publications = registry_rows(root, "publications.csv")
    identifiers = registry_rows(root, "work_identifiers.csv")
    taxonomy = registry_rows(root, "taxonomy.csv")
    summaries = registry_rows(root, "editorial_summary.csv")
    versions = registry_rows(root, "archive_versions.csv")

    topic_labels = {
        (row.get("code") or "").strip(): (row.get("label") or "").strip()
        for row in taxonomy
        if (row.get("dimension") or "").strip() == "topic"
    }
    records = build_records(
        papers, events, decisions, publications, identifiers, topic_labels
    )
    current_publications = current_publication_rows(publications)
    summary = current_singleton(summaries, "editorial_summary.csv")
    version = current_singleton(versions, "archive_versions.csv")

    metadata_fix = as_nonnegative_int(summary, "metadata_fix")
    manual_review = as_nonnegative_int(summary, "manual_review")
    abstract_review = as_nonnegative_int(summary, "abstract_review")
    rejected = as_nonnegative_int(summary, "rejected_omitted")
    core = sum(
        record["screeningDecision"] == "eligible_core" for record in records
    )
    contextual = len(records) - core

    return {
        "schemaVersion": int(version["schema_version"]),
        "archiveVersion": version["version"],
        "protocolVersion": version["protocol_version"],
        "releaseDate": version["release_date"],
        "searchCoverageThrough": version["search_coverage_through"],
        "sourceSnapshot": source_snapshot(
            [*papers, *decisions, *current_publications, summary, version]
        ),
        "methodology": {
            "includedDefinition": (
                "Records pass the canonical, discovery, current eligibility and "
                "explicit publication-manifest gates."
            ),
            "editorialDefinition": (
                "Aggregate editorial counts are published separately; candidate "
                "metadata and reviewer notes are not included in the archive export."
            ),
            "rejectedRecordsOmitted": rejected,
        },
        "counts": {
            "records": len(records),
            "included": len(records),
            "core": core,
            "contextual": contextual,
            "editorialQueue": metadata_fix + manual_review + abstract_review,
            "metadataFix": metadata_fix,
            "manualReview": manual_review,
            "abstractReview": abstract_review,
            "rejectedOmitted": rejected,
        },
        "records": records,
    }


def write_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "archive.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    csv_fields = [field for field in PUBLIC_RECORD_FIELDS if field != "links"]
    with (output_dir / "archive.csv").open(
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory for archive.json and archive.csv.",
    )
    args = parser.parse_args()
    payload = build_payload()
    write_outputs(payload, args.output_dir)
    counts = payload["counts"]
    print(
        "Built public archive "
        f"v{payload['archiveVersion']}: {counts['included']} published; "
        f"{counts['editorialQueue']} editorial and "
        f"{counts['rejectedOmitted']} rejected records omitted."
    )


if __name__ == "__main__":
    try:
        main()
    except (ArchiveBuildError, csv.Error, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
