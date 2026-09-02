#!/usr/bin/env python3
"""Validate CILE Review Ontology Profile conformance across governed artifacts.

The validator has no third-party dependencies. The normative LinkML file is
JSON-compatible YAML, so Python's stdlib JSON parser can validate it in CI while
remaining valid YAML for LinkML tooling.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "ontology/cile-review-profile.yaml"
CONTRACT_PATH = ROOT / "ontology/mappings/artifact-contracts.json"
EXTERNAL_PATH = ROOT / "ontology/mappings/external-vocabularies.json"
VOCAB_PATH = ROOT / "ontology/vocabularies/infiltration-relations.csv"
TTL_PATH = ROOT / "ontology/cile-review-profile.ttl"
PUBLIC_TTL_PATH = ROOT / "site/vocab/cile-review.ttl"
INTERCHANGE_SCHEMA = ROOT / "schema/cile-review-record.schema.json"

REQUIRED_PREFIXES = {
    "cile", "slr", "prov", "dcterms", "fabio", "bibo", "oa", "skos", "ripe"
}
REQUIRED_CLASSES = {
    "SystematicReview",
    "CandidateRecord",
    "ScholarlyWork",
    "Manifestation",
    "Identifier",
    "SearchActivity",
    "RetrievalActivity",
    "ScreeningActivity",
    "ScreeningDecision",
    "Evidence",
    "EvidenceSpan",
    "AbstractCoverageAssessment",
    "AccessAssessment",
    "CodingAssertion",
    "PublicationState",
    "WorkRelation",
    "ReviewEvent",
    "HumanAgent",
    "SoftwareAgent",
    "CriminalInfiltrationStudy",
}
REQUIRED_ENUMS = {
    "AccessStatusEnum",
    "AbstractStatusEnum",
    "CandidateStatusEnum",
    "ReviewStageEnum",
    "ScreeningDecisionEnum",
    "InfiltrationRelationEnum",
}
KNOWN_COMPATIBILITY_HEADERS = {
    "other_identifiers",
    "github_issue_number",
    "resolved_doi",
    "match_method",
    "match_score",
    "provider_errors",
    "providers_tried",
}
CONTENT_FORBIDDEN_HEADERS = {
    "abstract_text",
    "full_text",
    "full_text_text",
    "article_body",
    "document_body",
    "content_body",
}


class OntologyError(ValueError):
    pass


def fail(message: str) -> None:
    raise OntologyError(message)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"missing_ontology_artifact:{path.relative_to(ROOT)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid_json_compatible_yaml:{path.relative_to(ROOT)}:{exc}")
    if not isinstance(value, dict):
        fail(f"ontology_artifact_not_object:{path.relative_to(ROOT)}")
    return value


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        fail(f"missing_governed_artifact:{path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def normalise_doi(value: object) -> str:
    doi = " ".join(str(value or "").split()).lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi.strip().rstrip(".")


def enum_values(profile: dict[str, Any], enum_name: str) -> set[str]:
    enum = profile.get("enums", {}).get(enum_name)
    if not isinstance(enum, dict):
        fail(f"missing_enum:{enum_name}")
    values = enum.get("permissible_values", {})
    if not isinstance(values, dict):
        fail(f"invalid_enum:{enum_name}")
    return set(values)


def check_profile(profile: dict[str, Any], external: dict[str, Any]) -> None:
    if profile.get("version") != "0.1.0":
        fail(f"unexpected_profile_version:{profile.get('version')}")
    prefixes = profile.get("prefixes")
    classes = profile.get("classes")
    slots = profile.get("slots")
    enums = profile.get("enums")
    if not all(isinstance(value, dict) for value in (prefixes, classes, slots, enums)):
        fail("profile_sections_missing")
    missing_prefixes = sorted(REQUIRED_PREFIXES - set(prefixes))
    missing_classes = sorted(REQUIRED_CLASSES - set(classes))
    missing_enums = sorted(REQUIRED_ENUMS - set(enums))
    if missing_prefixes:
        fail(f"profile_missing_prefixes:{','.join(missing_prefixes)}")
    if missing_classes:
        fail(f"profile_missing_classes:{','.join(missing_classes)}")
    if missing_enums:
        fail(f"profile_missing_enums:{','.join(missing_enums)}")
    if external.get("profile_version") != profile.get("version"):
        fail("external_mapping_version_mismatch")
    dependencies = external.get("dependencies") or []
    names = {row.get("name") for row in dependencies if isinstance(row, dict)}
    for required in ("SynthScholar SLR Ontology", "W3C PROV-O", "SPAR FaBiO", "RIPE-O"):
        if required not in names:
            fail(f"missing_external_dependency:{required}")
    for class_name, spec in classes.items():
        if not isinstance(spec, dict):
            fail(f"invalid_class_spec:{class_name}")
        parent = spec.get("is_a")
        if parent and parent not in classes:
            fail(f"unknown_parent_class:{class_name}:{parent}")
        for slot in spec.get("slots", []) or []:
            if slot not in slots:
                fail(f"unknown_slot_on_class:{class_name}:{slot}")
    for slot_name, spec in slots.items():
        if not isinstance(spec, dict):
            fail(f"invalid_slot_spec:{slot_name}")
        range_name = spec.get("range")
        if range_name and range_name not in classes and range_name not in enums and range_name not in {
            "string", "integer", "boolean", "datetime", "uriorcurie"
        }:
            fail(f"unknown_slot_range:{slot_name}:{range_name}")


def semantic_target_valid(target: str, profile: dict[str, Any]) -> bool:
    if target in profile.get("slots", {}):
        return True
    if ":" not in target:
        return False
    prefix = target.split(":", 1)[0]
    return prefix in profile.get("prefixes", {})


def header_semantically_known(
    header: str,
    semantic_fields: dict[str, str],
    patterns: list[re.Pattern[str]],
) -> bool:
    if header in semantic_fields or header in KNOWN_COMPATIBILITY_HEADERS:
        return True
    return any(pattern.fullmatch(header) for pattern in patterns)


def validate_primary_key(path: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    if not fields:
        fail(f"missing_primary_key_contract:{path}")
    seen: set[tuple[str, ...]] = set()
    for index, row in enumerate(rows, start=2):
        key = tuple((row.get(field) or "").strip() for field in fields)
        if not all(key):
            fail(f"blank_primary_key:{path}:{index}:{fields}")
        if key in seen:
            fail(f"duplicate_primary_key:{path}:{key}")
        seen.add(key)


def key_index(rows: list[dict[str, str]], fields: list[str]) -> set[tuple[str, ...]]:
    return {
        tuple((row.get(field) or "").strip() for field in fields)
        for row in rows
        if all((row.get(field) or "").strip() for field in fields)
    }


def check_contracts(profile: dict[str, Any], contracts: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    if contracts.get("profile_version") != profile.get("version"):
        fail("artifact_contract_version_mismatch")
    artifacts = contracts.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        fail("artifact_contracts_missing")
    discovered: set[str] = set()
    for root_name in contracts.get("governed_roots", []):
        root = ROOT / root_name
        if not root.exists():
            fail(f"missing_governed_root:{root_name}")
        discovered.update(
            path.relative_to(ROOT).as_posix() for path in root.glob("*.csv")
        )
    declared = set(artifacts)
    if discovered != declared:
        missing = sorted(discovered - declared)
        stale = sorted(declared - discovered)
        fail(f"governed_artifact_mapping_mismatch:unmapped={missing}:stale={stale}")

    patterns = [re.compile(value) for value in contracts.get("field_families", [])]
    cache: dict[str, list[dict[str, str]]] = {}
    headers_by_path: dict[str, list[str]] = {}
    for path_name, contract in artifacts.items():
        if not isinstance(contract, dict):
            fail(f"invalid_artifact_contract:{path_name}")
        classes = contract.get("row_classes") or []
        for class_name in classes:
            if class_name not in profile.get("classes", {}):
                fail(f"artifact_unknown_class:{path_name}:{class_name}")
        path = ROOT / path_name
        headers, rows = read_csv(path)
        headers_by_path[path_name] = headers
        cache[path_name] = rows
        required = set(contract.get("required_fields") or [])
        missing_headers = sorted(required - set(headers))
        if missing_headers:
            fail(f"artifact_missing_fields:{path_name}:{missing_headers}")
        semantic_fields = contract.get("semantic_fields") or {}
        for field, target in semantic_fields.items():
            if field not in headers:
                # A semantic map may cover an optional field present in the stable schema
                # of a sibling branch; only required fields are hard-presence constraints.
                continue
            if not semantic_target_valid(str(target), profile):
                fail(f"unknown_semantic_target:{path_name}:{field}:{target}")
        unknown_headers = [
            header for header in headers
            if not header_semantically_known(header, semantic_fields, patterns)
        ]
        if unknown_headers:
            fail(f"undeclared_semantic_fields:{path_name}:{unknown_headers}")
        validate_primary_key(path_name, contract.get("primary_key") or [], rows)
        for field, enum_name in (contract.get("controlled_fields") or {}).items():
            allowed = enum_values(profile, enum_name)
            invalid = sorted({
                (row.get(field) or "").strip()
                for row in rows
                if (row.get(field) or "").strip() and (row.get(field) or "").strip() not in allowed
            })
            if invalid:
                fail(f"controlled_value_violation:{path_name}:{field}:{invalid}")

    for path_name, contract in artifacts.items():
        rows = cache[path_name]
        for fk in contract.get("foreign_keys") or []:
            fields = fk.get("fields") or []
            target_path = fk.get("target")
            target_fields = fk.get("target_fields") or []
            if target_path not in cache:
                fail(f"foreign_key_unknown_target:{path_name}:{target_path}")
            if len(fields) != len(target_fields) or not fields:
                fail(f"invalid_foreign_key_contract:{path_name}:{fields}:{target_fields}")
            target_index = key_index(cache[target_path], target_fields)
            for index, row in enumerate(rows, start=2):
                key = tuple((row.get(field) or "").strip() for field in fields)
                if not any(key):
                    if fk.get("allow_blank"):
                        continue
                    fail(f"blank_foreign_key:{path_name}:{index}:{fields}")
                if key not in target_index:
                    fail(f"foreign_key_violation:{path_name}:{index}:{key}:{target_path}")
    return cache


def check_vocabulary(profile: dict[str, Any]) -> None:
    fields, rows = read_csv(VOCAB_PATH)
    if fields != ["code", "label", "definition", "parent_code", "profile_version"]:
        fail(f"infiltration_vocabulary_fields:{fields}")
    codes = [row["code"].strip() for row in rows]
    if len(codes) != len(set(codes)) or not codes:
        fail("infiltration_vocabulary_codes_invalid")
    enum_codes = enum_values(profile, "InfiltrationRelationEnum")
    if set(codes) != enum_codes:
        fail(f"infiltration_vocabulary_profile_drift:{set(codes)}:{enum_codes}")
    for row in rows:
        if row["profile_version"] != profile["version"]:
            fail(f"infiltration_vocabulary_version:{row['code']}")
        if row["parent_code"] and row["parent_code"] not in enum_codes:
            fail(f"infiltration_vocabulary_parent:{row['code']}:{row['parent_code']}")


def check_serialisations(profile: dict[str, Any]) -> None:
    if not TTL_PATH.exists() or not PUBLIC_TTL_PATH.exists():
        fail("ontology_turtle_missing")
    source = TTL_PATH.read_text(encoding="utf-8")
    public = PUBLIC_TTL_PATH.read_text(encoding="utf-8")
    if source != public:
        fail("public_ontology_turtle_drift")
    for marker in (
        'owl:versionInfo "0.1.0"',
        "cile:ScholarlyWork a owl:Class",
        "cile:Manifestation a owl:Class",
        "cile:ScreeningDecision a owl:Class",
        "cile:AccessAssessment a owl:Class",
        "skos:exactMatch slr:IncludedSource",
        "skos:relatedMatch ripe:Answer",
    ):
        if marker not in source:
            fail(f"ontology_turtle_missing_marker:{marker}")
    schema = load_json(INTERCHANGE_SCHEMA)
    if not schema.get("$defs") or "ScholarlyWork" not in schema["$defs"]:
        fail("interchange_schema_missing_core_defs")
    if profile["version"] not in schema.get("description", ""):
        fail("interchange_schema_profile_version_missing")


def check_identity_and_provenance(data: dict[str, list[dict[str, str]]]) -> None:
    papers = data["data/registry/papers.csv"]
    identifiers = data["data/registry/work_identifiers.csv"]
    paper_ids = {row["paper_id"] for row in papers}
    primary_doi_by_work: dict[str, list[str]] = defaultdict(list)
    doi_owner: dict[str, str] = {}
    for row in identifiers:
        relation = row.get("relation", "").strip()
        scheme = row.get("scheme", "").strip().lower()
        is_primary = truthy(row.get("is_primary"))
        if relation == "manifestation" and is_primary:
            fail(f"manifestation_identifier_cannot_be_primary:{row.get('identifier_id')}")
        if scheme == "doi" and is_primary and relation == "canonical":
            doi = normalise_doi(row.get("value"))
            if not doi:
                fail(f"blank_primary_doi:{row.get('identifier_id')}")
            primary_doi_by_work[row["paper_id"]].append(doi)
            previous = doi_owner.get(doi)
            if previous and previous != row["paper_id"]:
                fail(f"canonical_doi_owned_by_multiple_works:{doi}:{previous}:{row['paper_id']}")
            doi_owner[doi] = row["paper_id"]
    for paper in papers:
        work_id = paper["paper_id"]
        if work_id not in paper_ids:
            fail(f"impossible_work_identity:{work_id}")
        denormalised = normalise_doi(paper.get("doi"))
        primaries = primary_doi_by_work.get(work_id, [])
        if denormalised:
            if len(primaries) != 1 or primaries[0] != denormalised:
                fail(f"canonical_doi_registry_mismatch:{work_id}:{denormalised}:{primaries}")
        elif primaries:
            fail(f"primary_doi_missing_from_papers:{work_id}:{primaries}")

    decisions = data["data/registry/screening_decisions.csv"]
    for row in decisions:
        if not row.get("reviewer", "").strip() or not row.get("decision_date", "").strip():
            fail(f"screening_decision_missing_attribution:{row.get('decision_id')}")

    queue = data["data/curation/review_queue.csv"]
    actions = data["data/curation/actions.csv"]
    candidate_ids = {row["candidate_id"] for row in queue}
    if candidate_ids & paper_ids:
        fail("candidate_and_canonical_identifier_spaces_overlap")
    action_by_id = {row["action_id"]: row for row in actions}
    for action in actions:
        for field in ("actor", "decided_at", "rationale", "evidence_basis"):
            if not action.get(field, "").strip():
                fail(f"curator_action_missing_provenance:{action.get('action_id')}:{field}")
    for row in queue:
        if row.get("current_status") == "pending":
            continue
        action_id = row.get("last_action_id", "").strip()
        if not action_id or action_id not in action_by_id:
            fail(f"decided_candidate_missing_review_event:{row['candidate_id']}")


def check_candidate_coverage(data: dict[str, list[dict[str, str]]]) -> None:
    queue = data["data/curation/review_queue.csv"]
    queue_ids = [row["candidate_id"] for row in queue]
    for path_name in (
        "data/curation/retrieval_coverage.csv",
        "data/curation/abstract_coverage.csv",
        "data/curation/access_coverage.csv",
    ):
        ids = [row["candidate_id"] for row in data[path_name]]
        if ids != queue_ids:
            fail(f"coverage_not_one_to_one_with_candidate_queue:{path_name}")
    evidence_ids = {row["candidate_id"] for row in data["data/curation/access_evidence.csv"]}
    if not evidence_ids <= set(queue_ids):
        fail(f"access_evidence_unknown_candidates:{sorted(evidence_ids - set(queue_ids))}")

    retrieval_by_id = {
        row["candidate_id"]: row for row in data["data/curation/retrieval_coverage.csv"]
    }
    for row in data["data/curation/access_coverage.csv"]:
        candidate_id = row["candidate_id"]
        status = row.get("access_status", "")
        if status == "open" and (
            not row.get("access_url", "").strip() or not row.get("evidence_source", "").strip()
        ):
            fail(f"open_access_without_positive_evidence:{candidate_id}")
        if status == "restricted":
            retrieval = retrieval_by_id.get(candidate_id, {})
            if retrieval.get("full_text_url", "").strip():
                fail(f"restricted_conflicts_with_governed_full_text:{candidate_id}")
            if not row.get("evidence_source", "").strip() or not row.get("evidence_detail", "").strip():
                fail(f"restricted_without_closed_evidence:{candidate_id}")

    abstract_fields, _ = read_csv(ROOT / "data/curation/abstract_coverage.csv")
    retrieval_fields, _ = read_csv(ROOT / "data/curation/retrieval_coverage.csv")
    for field in abstract_fields:
        if field.lower() in CONTENT_FORBIDDEN_HEADERS:
            fail(f"abstract_coverage_persists_content:{field}")
    for field in retrieval_fields:
        lowered = field.lower()
        if lowered in CONTENT_FORBIDDEN_HEADERS or "body" in lowered:
            fail(f"retrieval_coverage_persists_content:{field}")


def validate_all(*, quiet: bool = False) -> dict[str, int | str]:
    profile = load_json(PROFILE_PATH)
    external = load_json(EXTERNAL_PATH)
    contracts = load_json(CONTRACT_PATH)
    check_profile(profile, external)
    check_vocabulary(profile)
    check_serialisations(profile)
    data = check_contracts(profile, contracts)
    check_identity_and_provenance(data)
    check_candidate_coverage(data)
    result: dict[str, int | str] = {
        "profile_version": str(profile["version"]),
        "governed_artifacts": len(contracts["artifacts"]),
        "canonical_works": len(data["data/registry/papers.csv"]),
        "candidates": len(data["data/curation/review_queue.csv"]),
    }
    if not quiet:
        print(json.dumps(result, sort_keys=True))
        print("[OK] CILE ontology conformance passed.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    validate_all(quiet=args.quiet)


if __name__ == "__main__":
    try:
        main()
    except (csv.Error, json.JSONDecodeError, OSError, OntologyError) as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
