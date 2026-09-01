#!/usr/bin/env python3
"""Import one authorised daily intake manifest into the curator queue.

This is a mechanical staging step. It preserves the intake assessment and
required human action, but never converts them into eligibility or publication
decisions.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_FIELDS = {
    "candidate_id",
    "title",
    "authors",
    "year",
    "venue",
    "work_type",
    "identifiers",
    "source_links",
    "sources",
    "query_ids",
    "verification_status",
    "possible_duplicate",
    "metadata_conflict",
    "intake_assessment",
    "relevance_reason",
    "required_human_action",
}
WORK_TYPES = {
    "peer_reviewed",
    "accepted_manuscript",
    "working_paper",
    "preprint",
    "other",
    "unknown",
}
VERIFICATION = {"metadata_verified", "metadata_partial", "identifier_unresolved"}
ASSESSMENTS = {"plausible_core", "plausible_contextual", "uncertain"}
SEARCH_FIELDS = {"schema_version", "batch_id", "repository_commit", "sources"}
SEARCH_SOURCE_FIELDS = {"source", "queries"}
SEARCH_QUERY_FIELDS = {"query_id", "query_text"}
REQUIRED_SAFEGUARDS = (
    "No candidate was marked eligible or published.",
    "Canonical records and existing intake issues were checked for duplicates.",
    "No copyrighted full text or long abstract is included.",
)


class IntakeImportError(ValueError):
    """Raised when an intake issue cannot be staged safely."""


def clean(value: object, maximum: int = 2000) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise IntakeImportError("Expected text value")
    value = " ".join(value.split())
    if len(value) > maximum:
        raise IntakeImportError(f"Text exceeds {maximum} characters")
    return value


def required(value: object, label: str, maximum: int = 500) -> str:
    value = clean(value, maximum)
    if not value:
        raise IntakeImportError(f"{label} is required")
    return value


def normalise_doi(value: object) -> str:
    doi = clean(value, 200).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return doi


def issue_form_value(body: str, label: str) -> str:
    pattern = re.compile(
        rf"(?m)^###\s+{re.escape(label)}\s*$\n+(?P<value>.*?)(?=^###\s+|\Z)",
        re.DOTALL,
    )
    matches = list(pattern.finditer((body or "").replace("\r\n", "\n")))
    if len(matches) != 1:
        raise IntakeImportError(f"Issue form must contain one {label!r} section")
    return matches[0].group("value").strip()


def parse_json_section(body: str, label: str) -> dict[str, object]:
    section = issue_form_value(body, label)
    match = re.fullmatch(r"```json\s*(\{.*\})\s*```", section, re.DOTALL)
    if not match:
        raise IntakeImportError(f"{label} must be one JSON object")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise IntakeImportError(f"{label} JSON is invalid") from exc
    if not isinstance(value, dict):
        raise IntakeImportError(f"{label} must contain a JSON object")
    return value


def parse_search_manifest(body: str, batch_id: str) -> dict[str, str]:
    manifest = parse_json_section(body, "Search and provenance log")
    if set(manifest) != SEARCH_FIELDS:
        raise IntakeImportError("Search and provenance log fields are invalid")
    commit = manifest["repository_commit"]
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["batch_id"] != batch_id
        or not isinstance(commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", commit)
    ):
        raise IntakeImportError("Search and provenance log identity is invalid")
    sources = manifest["sources"]
    if not isinstance(sources, list) or len(sources) != 2:
        raise IntakeImportError("Search and provenance log must contain two sources")
    query_sources: dict[str, str] = {}
    seen_sources: set[str] = set()
    for source_index, source in enumerate(sources):
        label = f"search.sources[{source_index}]"
        if not isinstance(source, dict) or set(source) != SEARCH_SOURCE_FIELDS:
            raise IntakeImportError(f"{label}: fields are invalid")
        source_name = source["source"]
        if source_name not in {"Consensus", "Exa"} or source_name in seen_sources:
            raise IntakeImportError(f"{label}.source is invalid or duplicated")
        seen_sources.add(source_name)
        queries = source["queries"]
        if not isinstance(queries, list) or not 1 <= len(queries) <= 100:
            raise IntakeImportError(f"{label}.queries is invalid")
        prefix = "CONSENSUS" if source_name == "Consensus" else "EXA"
        for query_index, query in enumerate(queries):
            query_label = f"{label}.queries[{query_index}]"
            if not isinstance(query, dict) or set(query) != SEARCH_QUERY_FIELDS:
                raise IntakeImportError(f"{query_label}: fields are invalid")
            query_id = required(query["query_id"], f"{query_label}.query_id", 80)
            if (
                not re.fullmatch(rf"{prefix}-[A-Z0-9][A-Z0-9._-]*", query_id)
                or query_id in query_sources
            ):
                raise IntakeImportError(f"{query_label}.query_id is invalid or duplicated")
            required(query["query_text"], f"{query_label}.query_text", 2000)
            query_sources[query_id] = source_name
    if seen_sources != {"Consensus", "Exa"}:
        raise IntakeImportError("Search and provenance log source set is incomplete")
    return query_sources


def parse_manifest(body: str, query_sources: dict[str, str] | None = None) -> dict[str, object]:
    manifest = parse_json_section(body, "Candidate records")
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "batch_id",
        "candidates",
    }:
        raise IntakeImportError("Candidate manifest fields are invalid")
    batch_id = manifest["batch_id"]
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or not isinstance(batch_id, str)
    ):
        raise IntakeImportError("Candidate manifest version or batch is invalid")
    if not re.fullmatch(r"ACADEMIC-\d{4}-\d{2}-\d{2}", batch_id):
        raise IntakeImportError("Candidate manifest batch ID is invalid")
    try:
        date.fromisoformat(batch_id.removeprefix("ACADEMIC-"))
    except ValueError as exc:
        raise IntakeImportError("Candidate manifest batch date is invalid") from exc
    candidates = manifest["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 500:
        raise IntakeImportError("Candidate manifest must contain 1 to 500 records")
    expected_id = re.compile(rf"CAND-{re.escape(batch_id)}-\d{{3}}")
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        label = f"candidates[{index}]"
        if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_FIELDS:
            raise IntakeImportError(f"{label}: fields are invalid")
        candidate_id = required(candidate["candidate_id"], f"{label}.candidate_id", 80)
        if not expected_id.fullmatch(candidate_id) or candidate_id in seen:
            raise IntakeImportError(f"{label}.candidate_id is invalid or duplicated")
        seen.add(candidate_id)
        required(candidate["title"], f"{label}.title")
        authors = candidate["authors"]
        if not isinstance(authors, list) or not authors or len(authors) > 50:
            raise IntakeImportError(f"{label}.authors is invalid")
        authors = [required(author, f"{label}.authors[]", 300) for author in authors]
        if len(authors) != len(set(authors)):
            raise IntakeImportError(f"{label}.authors contains duplicates")
        year = candidate["year"]
        if year is not None and (
            isinstance(year, bool) or not isinstance(year, int) or not 1800 <= year <= 2100
        ):
            raise IntakeImportError(f"{label}.year is invalid")
        if candidate["venue"] is not None:
            required(candidate["venue"], f"{label}.venue", 300)
        if candidate["work_type"] not in WORK_TYPES:
            raise IntakeImportError(f"{label}.work_type is invalid")
        identifiers = candidate["identifiers"]
        if not isinstance(identifiers, dict) or set(identifiers) != {"doi", "other"}:
            raise IntakeImportError(f"{label}.identifiers is invalid")
        if identifiers["doi"] is not None:
            if not normalise_doi(identifiers["doi"]):
                raise IntakeImportError(f"{label}.identifiers.doi is invalid")
        if not isinstance(identifiers["other"], list) or len(identifiers["other"]) > 20:
            raise IntakeImportError(f"{label}.identifiers.other is invalid")
        other_identifiers = [
            required(identifier, f"{label}.identifiers.other[]", 200)
            for identifier in identifiers["other"]
        ]
        if len(other_identifiers) != len(set(other_identifiers)):
            raise IntakeImportError(f"{label}.identifiers.other contains duplicates")
        links = candidate["source_links"]
        if not isinstance(links, list) or not links or len(links) > 20:
            raise IntakeImportError(f"{label}.source_links is invalid")
        validated_links: list[str] = []
        for link in links:
            link = required(link, f"{label}.source_links[]", 1000)
            parsed = urlsplit(link)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise IntakeImportError(f"{label}.source_links contains an invalid URL")
            validated_links.append(link)
        if len(validated_links) != len(set(validated_links)):
            raise IntakeImportError(f"{label}.source_links contains duplicates")
        sources = candidate["sources"]
        if (
            not isinstance(sources, list)
            or not sources
            or len(sources) > 2
        ):
            raise IntakeImportError(f"{label}.sources is invalid")
        validated_sources = [
            required(source, f"{label}.sources[]", 40) for source in sources
        ]
        if (
            not set(validated_sources).issubset({"Consensus", "Exa"})
            or len(validated_sources) != len(set(validated_sources))
        ):
            raise IntakeImportError(f"{label}.sources is invalid")
        query_ids = candidate["query_ids"]
        if (
            not isinstance(query_ids, list)
            or not query_ids
            or len(query_ids) > 20
        ):
            raise IntakeImportError(f"{label}.query_ids is invalid")
        validated_query_ids = [
            required(query_id, f"{label}.query_ids[]", 80)
            for query_id in query_ids
        ]
        if len(validated_query_ids) != len(set(validated_query_ids)):
            raise IntakeImportError(f"{label}.query_ids contains duplicates")
        if query_sources is not None:
            if any(query_id not in query_sources for query_id in validated_query_ids):
                raise IntakeImportError(f"{label}.query_ids contains an unknown query")
            if {
                query_sources[query_id] for query_id in validated_query_ids
            } != set(validated_sources):
                raise IntakeImportError(f"{label}.query_ids disagrees with sources")
        if candidate["verification_status"] not in VERIFICATION:
            raise IntakeImportError(f"{label}.verification_status is invalid")
        if candidate["intake_assessment"] not in ASSESSMENTS:
            raise IntakeImportError(f"{label}.intake_assessment is invalid")
        required(candidate["relevance_reason"], f"{label}.relevance_reason", 1000)
        required(
            candidate["required_human_action"],
            f"{label}.required_human_action",
            500,
        )
        for optional in ("possible_duplicate", "metadata_conflict"):
            if candidate[optional] is not None:
                required(candidate[optional], f"{label}.{optional}", 500)
    return manifest


def parse_intake_issue(body: str, title: str) -> dict[str, object]:
    batch_id = issue_form_value(body, "Batch ID")
    if not re.fullmatch(r"ACADEMIC-\d{4}-\d{2}-\d{2}", batch_id):
        raise IntakeImportError("Batch ID section is invalid")
    if title.strip() != f"[INTAKE][ACADEMIC] {batch_id}":
        raise IntakeImportError("Issue title disagrees with the batch ID")
    query_sources = parse_search_manifest(body, batch_id)
    manifest = parse_manifest(body, query_sources)
    if manifest["batch_id"] != batch_id:
        raise IntakeImportError("Candidate manifest disagrees with the batch ID")
    safeguards = issue_form_value(body, "Safeguards")
    lines = [line.strip() for line in safeguards.splitlines() if line.strip()]
    if len(lines) != len(REQUIRED_SAFEGUARDS):
        raise IntakeImportError(
            "Safeguards section must contain exactly three confirmations"
        )
    for phrase in REQUIRED_SAFEGUARDS:
        pattern = re.compile(rf"- \[[xX]\] {re.escape(phrase)}")
        if sum(pattern.fullmatch(line) is not None for line in lines) != 1:
            raise IntakeImportError(
                f"Safeguards section must check exactly once: {phrase}"
            )
    return manifest


def read_queue(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise IntakeImportError("review_queue.csv has no header")
        return list(reader.fieldnames), [dict(row) for row in reader]


def import_candidates(
    root: Path,
    body: str,
    issue_title: str,
    issue_number: str,
    imported_at: str,
) -> dict[str, object]:
    try:
        imported_at = date.fromisoformat(imported_at).isoformat()
    except ValueError as exc:
        raise IntakeImportError("Import date must use YYYY-MM-DD") from exc
    if not re.fullmatch(r"\d+", issue_number):
        raise IntakeImportError("GitHub issue number is invalid")
    manifest = parse_intake_issue(body, issue_title)
    batch_date = date.fromisoformat(str(manifest["batch_id"]).removeprefix("ACADEMIC-"))
    if date.fromisoformat(imported_at) < batch_date:
        raise IntakeImportError("Import date cannot precede the intake batch")
    path = root / "data" / "curation" / "review_queue.csv"
    fields, queue = read_queue(path)
    required_fields = {
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
        "intake_assessment",
        "intake_reason",
        "possible_duplicate",
        "metadata_conflict",
        "required_human_action",
        "origin",
        "review_stage",
        "current_status",
        "materialised_at",
        "updated_at",
        "provenance",
    }
    if required_fields - set(fields):
        raise IntakeImportError(
            "review_queue.csv is missing field(s): "
            + ", ".join(sorted(required_fields - set(fields)))
        )
    existing = {row["candidate_id"] for row in queue}
    candidates = manifest["candidates"]
    assert isinstance(candidates, list)
    incoming = {str(candidate["candidate_id"]) for candidate in candidates}
    overlap = sorted(existing & incoming)
    if overlap:
        raise IntakeImportError(
            "Candidate(s) already materialised: " + ", ".join(overlap)
        )
    batch_marker = f"batch:{manifest['batch_id']}"
    if any(batch_marker in row.get("provenance", "") for row in queue):
        raise IntakeImportError(f"Intake batch {manifest['batch_id']} is already staged")
    added: list[str] = []
    for candidate in candidates:
        identifiers = candidate["identifiers"]
        verification = str(candidate["verification_status"])
        stage = (
            "metadata_fix"
            if verification != "metadata_verified" or candidate["metadata_conflict"]
            else "abstract_full_text_review"
        )
        row = {field: "" for field in fields}
        row.update(
            {
                "candidate_id": str(candidate["candidate_id"]),
                "title": clean(candidate["title"], 500),
                "doi": normalise_doi(identifiers["doi"]),
                "authors": "; ".join(clean(value, 300) for value in candidate["authors"]),
                "year": "" if candidate["year"] is None else str(candidate["year"]),
                "venue": clean(candidate["venue"], 300),
                "work_type": str(candidate["work_type"]),
                "source": " + ".join(
                    clean(value, 40) for value in candidate["sources"]
                ),
                "source_links": "; ".join(
                    clean(value, 1000) for value in candidate["source_links"]
                ),
                "other_identifiers": "; ".join(
                    clean(value, 200) for value in identifiers["other"]
                ),
                "source_query_id": "; ".join(
                    clean(value, 80) for value in candidate["query_ids"]
                ),
                "verification_status": verification,
                "metadata_confidence": (
                    "high" if verification == "metadata_verified" else ""
                ),
                "intake_assessment": str(candidate["intake_assessment"]),
                "intake_reason": clean(candidate["relevance_reason"], 1000),
                "possible_duplicate": clean(candidate["possible_duplicate"], 500),
                "metadata_conflict": clean(candidate["metadata_conflict"], 500),
                "required_human_action": clean(
                    candidate["required_human_action"], 500
                ),
                "origin": "daily_surveillance",
                "legacy_scope_fit": "",
                "legacy_recommendation": "",
                "legacy_reason": "",
                "legacy_priority": "",
                "review_stage": stage,
                "current_status": "pending",
                "current_decision": "",
                "exclusion_reason_code": "",
                "topic_code": "",
                "duplicate_target_id": "",
                "secondary_collection_code": "",
                "secondary_collection_rationale": "",
                "last_action_id": "",
                "materialised_at": imported_at,
                "updated_at": imported_at,
                "provenance": (
                    f"github-issue:#{issue_number};batch:{manifest['batch_id']}"
                ),
            }
        )
        queue.append(row)
        added.append(row["candidate_id"])
    queue.sort(key=lambda row: row["candidate_id"])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(queue)
    return {
        "batch_id": manifest["batch_id"],
        "issue_number": issue_number,
        "added": added,
        "queue_total": len(queue),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--issue-body-file", type=Path, required=True)
    parser.add_argument("--issue-title-file", type=Path, required=True)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--date", dest="imported_at", required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = import_candidates(
        args.root.resolve(),
        args.issue_body_file.read_text(encoding="utf-8"),
        args.issue_title_file.read_text(encoding="utf-8"),
        args.issue_number,
        args.imported_at,
    )
    if args.output:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"[OK] Staged {len(result['added'])} candidate(s) from "
        f"{result['batch_id']} without screening or publication changes."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, json.JSONDecodeError, IntakeImportError) as exc:
        raise SystemExit(f"[INTAKE BLOCKED] {exc}") from exc
