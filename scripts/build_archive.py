#!/usr/bin/env python3
"""Build the public literature-archive dataset from governed repository data.

The public archive contains canonical records from ``data/registry/papers.csv``
only. Editorial candidates and excluded records are counted for transparent
pipeline reporting, but their bibliographic metadata are never published.

No metadata is enriched or inferred by this script. It only transforms fields
already stored in the repository and produces deterministic JSON/CSV exports.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/registry/papers.csv"
DECISIONS = ROOT / "data/registry/screening_decisions.csv"
AUDITED_STAGING = ROOT / "data/raw/e0_seed_promotion_staging_audited.csv"
REVIEWED_CANDIDATES = ROOT / "data/raw/e0_verified_seed_candidates_reviewed.csv"
VERIFICATION_MATRIX = ROOT / "data/raw/e0_seed_verification_matrix.csv"
DEFAULT_OUTPUT_DIR = ROOT / "site/data"

TOPIC_LABELS = {
    "conceptual_theoretical": "Conceptual foundations",
    "mafia_legal_business": "Mafia and legal business",
    "criminal_firms": "Criminal firms",
    "procurement_market_capture": "Public procurement and market capture",
    "sectoral_infiltration": "Sectoral infiltration",
    "ownership_corporate_control": "Ownership and corporate control",
    "laundering_legal_business": "Laundering through legal business",
    "money_laundering_legal_economy": "Laundering through legal business",
    "methodological": "Methods and measurement",
    "identifier_resolution_noise": "Identifier review",
}

STATUS_LABELS = {
    "included": "Included seed",
}

STATUS_DESCRIPTIONS = {
    "included": (
        "Canonical E0 record imported after the pre-import audit. This is a "
        "seed inclusion, not a completed full-review judgement."
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def normalise_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def clean_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    return value.lower()


def record_key(row: dict[str, str]) -> str:
    doi = clean_doi(row.get("doi", "") or row.get("verified_doi", ""))
    if doi:
        return f"doi:{doi}"
    title = row.get("title", "") or row.get("verified_title", "")
    year = row.get("year", "") or row.get("verified_year", "")
    return f"title:{normalise_title(title)}|{year.strip()}"


def nonempty(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def public_topic(code: str) -> str:
    return TOPIC_LABELS.get(code, code.replace("_", " ").strip().title())


def public_links(doi: str, openalex_id: str) -> dict[str, str]:
    links: dict[str, str] = {}
    if doi:
        links["doi"] = f"https://doi.org/{doi}"
    if openalex_id:
        links["openalex"] = openalex_id
    return links


def year_value(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def source_snapshot(rows: Iterable[dict[str, str]]) -> str:
    dates: list[str] = []
    for row in rows:
        for key in ("updated_at", "created_at", "added_at", "decision_date"):
            value = (row.get(key) or "").strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                dates.append(value)
    return max(dates, default="2026-04-29")


def canonical_records(
    papers: list[dict[str, str]],
    decisions: list[dict[str, str]],
    audited_by_key: dict[str, dict[str, str]],
    candidates_by_key: dict[str, dict[str, str]],
    verification_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    decision_by_paper: dict[str, dict[str, str]] = {}
    for decision in decisions:
        if decision.get("is_current", "").strip().lower() == "true":
            decision_by_paper[decision.get("paper_id", "")] = decision

    records: list[dict[str, Any]] = []
    for paper in papers:
        key = record_key(paper)
        audit = audited_by_key.get(key, {})
        candidate = candidates_by_key.get(key, {})
        verification = verification_by_id.get(audit.get("seed_id", ""), {})
        decision = decision_by_paper.get(paper.get("paper_id", ""), {})
        doi = clean_doi(paper.get("doi", ""))
        topic_code = nonempty(
            audit.get("seed_category"), candidate.get("seed_stratum_review")
        )
        records.append(
            {
                "id": paper.get("paper_id", ""),
                "sourceId": audit.get("seed_id", ""),
                "section": "included",
                "status": "included",
                "statusLabel": STATUS_LABELS["included"],
                "statusDescription": STATUS_DESCRIPTIONS["included"],
                "title": paper.get("title", "").strip(),
                "authors": paper.get("authors", "").strip(),
                "year": year_value(paper.get("year", "")),
                "venue": paper.get("venue", "").strip(),
                "documentType": paper.get("document_type", "").strip(),
                "language": paper.get("language", "").strip(),
                "abstractAvailable": bool(paper.get("abstract", "").strip()),
                "doi": doi,
                "openalexId": candidate.get("openalex_id", "").strip(),
                "links": public_links(doi, candidate.get("openalex_id", "").strip()),
                "topicCode": topic_code,
                "topicLabel": public_topic(topic_code),
                "scopeFit": nonempty(
                    candidate.get("scope_fit"),
                    verification.get("scope_fit_after_verification"),
                    "direct",
                ),
                "metadataConfidence": nonempty(
                    candidate.get("metadata_confidence"),
                    verification.get("metadata_confidence"),
                ),
                "reason": nonempty(
                    audit.get("reason_for_seed_inclusion"),
                    candidate.get("review_reason"),
                ),
                "screeningDecision": decision.get("decision", "").strip(),
                "sourceBasis": nonempty(
                    audit.get("source_basis"), candidate.get("source")
                ),
            }
        )
    return records


def build_payload() -> dict[str, Any]:
    papers = read_csv(REGISTRY)
    decisions = read_csv(DECISIONS)
    audited = read_csv(AUDITED_STAGING)
    reviewed = read_csv(REVIEWED_CANDIDATES)
    verification = read_csv(VERIFICATION_MATRIX)

    audited_by_key = {record_key(row): row for row in audited}
    candidates_by_key = {record_key(row): row for row in reviewed}
    verification_by_id = {row.get("seed_id", ""): row for row in verification}

    records = canonical_records(
        papers,
        decisions,
        audited_by_key,
        candidates_by_key,
        verification_by_id,
    )
    records.sort(
        key=lambda row: (
            -(row["year"] or 0),
            normalise_title(row["title"]),
        )
    )

    status_counts = Counter(record["status"] for record in records)
    metadata_fix_count = sum(
        1 for row in audited if row.get("pre_import_decision") == "import_after_metadata_fix"
    )
    manual_review_count = sum(
        1 for row in audited if row.get("pre_import_decision") == "hold_for_manual_review"
    )
    abstract_review_count = sum(
        1
        for row in reviewed
        if row.get("final_recommendation") == "keep_candidate_pending_abstract_review"
    )
    rejected_count = sum(
        1 for row in reviewed if row.get("final_recommendation") == "reject"
    )
    snapshot = source_snapshot([*papers, *decisions, *audited, *reviewed])
    return {
        "schemaVersion": 1,
        "sourceSnapshot": snapshot,
        "methodology": {
            "includedDefinition": STATUS_DESCRIPTIONS["included"],
            "editorialDefinition": (
                "Candidate and excluded records remain in non-public editorial "
                "files until a governed inclusion decision is recorded."
            ),
            "rejectedRecordsOmitted": rejected_count,
        },
        "counts": {
            "records": len(records),
            "included": status_counts["included"],
            "editorialQueue": metadata_fix_count
            + manual_review_count
            + abstract_review_count,
            "metadataFix": metadata_fix_count,
            "manualReview": manual_review_count,
            "abstractReview": abstract_review_count,
            "rejectedOmitted": rejected_count,
        },
        "records": records,
    }


def write_outputs(payload: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "archive.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    csv_fields = [
        "id",
        "section",
        "status",
        "title",
        "authors",
        "year",
        "venue",
        "doi",
        "topicCode",
        "topicLabel",
        "scopeFit",
        "metadataConfidence",
        "reason",
        "sourceBasis",
    ]
    with (output_dir / "archive.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payload["records"])


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
        "Built public archive: "
        f"{counts['included']} included; {counts['editorialQueue']} editorial "
        f"records and {counts['rejectedOmitted']} rejected records omitted."
    )


if __name__ == "__main__":
    main()
