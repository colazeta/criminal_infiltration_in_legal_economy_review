#!/usr/bin/env python3
"""Apply one explicit candidate-screening instruction from a GitHub issue form.

The action is confined to `data/curation/`: it records a human instruction and
updates the current queue projection. It never creates canonical records or a
publication approval.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISIONS = {
    "eligible_core",
    "eligible_contextual",
    "maybe_full_text_needed",
    "not_eligible",
    "duplicate",
    "not_academic",
    "not_retrievable",
}
STAGES = {"title_abstract", "full_text", "seed_validation"}
CONFIDENCE = {"low", "medium", "high"}
STATUS_BY_DECISION = {
    "eligible_core": "screened_eligible_core",
    "eligible_contextual": "screened_eligible_contextual",
    "maybe_full_text_needed": "needs_full_text",
    "not_eligible": "screened_not_eligible",
    "duplicate": "duplicate_confirmed",
    "not_academic": "screened_not_academic",
    "not_retrievable": "screened_not_retrievable",
}
ISSUE_LABELS = {
    "Candidate ID": "candidate_id",
    "Screening stage": "screening_stage",
    "Decision": "decision",
    "Exclusion reason": "exclusion_reason_code",
    "Topic code": "topic_code",
    "Duplicate target": "duplicate_target_id",
    "Secondary collection": "secondary_collection_code",
    "Secondary collection relevance": "secondary_collection_rationale",
    "Confidence": "confidence",
    "Evidence basis and locator": "evidence_basis",
    "Record-specific rationale": "rationale",
    "Confirmation": "confirmation",
}


class CandidateDecisionError(ValueError):
    """Raised when a candidate instruction is incomplete or inconsistent."""


def clean(value: str | None) -> str:
    text = (value or "").strip()
    if text == "_No response_" or text == "NOT_APPLICABLE":
        return ""
    return text


def require_text(value: str, label: str, maximum: int = 2000) -> str:
    value = clean(value)
    if not value:
        raise CandidateDecisionError(f"{label} is required")
    if len(value) > maximum:
        raise CandidateDecisionError(f"{label} exceeds {maximum} characters")
    return value


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CandidateDecisionError(f"{path.name} has no header")
        rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows


def write_table(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_issue_form(body: str) -> dict[str, str]:
    sections = {
        match.group(1).strip(): clean(match.group(2))
        for match in re.finditer(
            r"^###\s+(.+?)\s*\n\n(.*?)(?=\n\n###\s+|\Z)",
            body or "",
            flags=re.MULTILINE | re.DOTALL,
        )
    }
    missing = [label for label in ISSUE_LABELS if label not in sections]
    if missing:
        raise CandidateDecisionError(
            f"Issue form is missing section(s): {', '.join(missing)}"
        )
    return {field: sections[label] for label, field in ISSUE_LABELS.items()}


def next_action_id(rows: list[dict[str, str]]) -> str:
    numbers: list[int] = []
    for row in rows:
        match = re.fullmatch(r"CA(\d{6})", row.get("action_id", ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"CA{max(numbers, default=0) + 1:06d}"


def validate_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise CandidateDecisionError("decision date must use YYYY-MM-DD") from exc


def validate_instruction(
    values: dict[str, str],
    queue: list[dict[str, str]],
    papers: list[dict[str, str]],
    taxonomy: list[dict[str, str]],
    reasons: list[dict[str, str]],
    secondary_collections: list[dict[str, str]],
) -> dict[str, str]:
    values = {key: clean(value) for key, value in values.items()}
    if values.get("confirmation") != "APPLY":
        raise CandidateDecisionError('confirmation must be exactly "APPLY"')
    candidate_id = require_text(values.get("candidate_id", ""), "candidate ID", 40)
    candidates = {row["candidate_id"]: row for row in queue}
    if candidate_id not in candidates:
        raise CandidateDecisionError(f"Unknown candidate ID: {candidate_id}")
    decision = values.get("decision", "")
    if decision not in DECISIONS:
        raise CandidateDecisionError(f"Unsupported decision: {decision}")
    stage = values.get("screening_stage", "")
    if stage not in STAGES:
        raise CandidateDecisionError(f"Unsupported screening stage: {stage}")
    confidence = values.get("confidence", "")
    if confidence not in CONFIDENCE:
        raise CandidateDecisionError(f"Unsupported confidence: {confidence}")
    require_text(values.get("evidence_basis", ""), "evidence basis")
    require_text(values.get("rationale", ""), "record-specific rationale")

    reason_code = values.get("exclusion_reason_code", "")
    topic_code = values.get("topic_code", "")
    duplicate_target = values.get("duplicate_target_id", "")
    secondary_collection = values.get("secondary_collection_code", "")
    secondary_rationale = values.get("secondary_collection_rationale", "")
    valid_reasons = {row["code"] for row in reasons}
    valid_topics = {
        row["code"] for row in taxonomy if row.get("dimension") == "topic"
    }
    valid_secondary_collections = {
        row["collection_code"] for row in secondary_collections
    }

    if secondary_collection:
        if decision != "not_eligible":
            raise CandidateDecisionError(
                "A secondary collection can be assigned only with not_eligible"
            )
        if secondary_collection not in valid_secondary_collections:
            raise CandidateDecisionError(
                "Secondary collection must use a governed collection code"
            )
        values["secondary_collection_rationale"] = require_text(
            secondary_rationale, "secondary collection relevance"
        )
    elif secondary_rationale:
        raise CandidateDecisionError(
            "Secondary collection relevance requires a secondary collection"
        )

    if decision in {"eligible_core", "eligible_contextual"}:
        if topic_code not in valid_topics:
            raise CandidateDecisionError(
                "An eligible decision requires a governed topic code"
            )
        if reason_code or duplicate_target:
            raise CandidateDecisionError(
                "Eligible decisions cannot carry an exclusion or duplicate target"
            )
    elif decision == "maybe_full_text_needed":
        if reason_code or topic_code or duplicate_target:
            raise CandidateDecisionError(
                "A full-text-needed decision cannot carry topic, exclusion or duplicate fields"
            )
    elif decision == "duplicate":
        if reason_code and reason_code != "DUPLICATE_RECORD":
            raise CandidateDecisionError(
                "Duplicate decisions must use DUPLICATE_RECORD"
            )
        if not duplicate_target:
            raise CandidateDecisionError("Duplicate target is required")
        known_targets = set(candidates) | {row["paper_id"] for row in papers}
        if duplicate_target not in known_targets:
            raise CandidateDecisionError(
                f"Unknown duplicate target: {duplicate_target}"
            )
        if duplicate_target == candidate_id:
            raise CandidateDecisionError("Candidate cannot duplicate itself")
        values["exclusion_reason_code"] = "DUPLICATE_RECORD"
        if topic_code:
            raise CandidateDecisionError("Duplicate decisions cannot assign a topic")
    else:
        expected_special = {
            "not_academic": "NOT_ACADEMIC_SOURCE",
            "not_retrievable": "FULL_TEXT_UNAVAILABLE",
        }.get(decision)
        if reason_code not in valid_reasons:
            raise CandidateDecisionError(
                "A non-eligible decision requires a governed exclusion reason"
            )
        if expected_special and reason_code != expected_special:
            raise CandidateDecisionError(
                f"{decision} must use {expected_special}"
            )
        if decision == "not_eligible" and reason_code in {
            "DUPLICATE_RECORD",
            "NOT_ACADEMIC_SOURCE",
            "FULL_TEXT_UNAVAILABLE",
        }:
            raise CandidateDecisionError(
                f"Use the matching dedicated decision for {reason_code}"
            )
        if topic_code or duplicate_target:
            raise CandidateDecisionError(
                "Excluded decisions cannot assign a topic or duplicate target"
            )
    return values


def apply_decision(
    root: Path,
    issue_body: str,
    actor: str,
    issue_number: str,
    decided_at: str,
) -> dict[str, str]:
    actor = require_text(actor, "curator identity", 100)
    issue_number = require_text(issue_number, "GitHub issue number", 20)
    decided_at = validate_date(decided_at)
    curation = root / "data" / "curation"
    queue_fields, queue = read_table(curation / "review_queue.csv")
    action_fields, actions = read_table(curation / "actions.csv")
    _, papers = read_table(root / "data" / "registry" / "papers.csv")
    _, taxonomy = read_table(root / "data" / "registry" / "taxonomy.csv")
    _, reasons = read_table(root / "data" / "registry" / "exclusion_reasons.csv")
    _, secondary_collections = read_table(
        root / "data" / "registry" / "secondary_collections.csv"
    )
    if any(row.get("github_issue_number") == issue_number for row in actions):
        raise CandidateDecisionError(
            f"GitHub issue #{issue_number} has already produced a curator action"
        )
    values = validate_instruction(
        parse_issue_form(issue_body),
        queue,
        papers,
        taxonomy,
        reasons,
        secondary_collections,
    )
    candidate = next(
        row for row in queue if row["candidate_id"] == values["candidate_id"]
    )
    previous_status = candidate["current_status"]
    new_status = STATUS_BY_DECISION[values["decision"]]
    action_id = next_action_id(actions)
    action = {
        "action_id": action_id,
        "candidate_id": values["candidate_id"],
        "github_issue_number": issue_number,
        "operation": "record_screening",
        "screening_stage": values["screening_stage"],
        "decision": values["decision"],
        "exclusion_reason_code": values["exclusion_reason_code"],
        "topic_code": values["topic_code"],
        "duplicate_target_id": values["duplicate_target_id"],
        "secondary_collection_code": values["secondary_collection_code"],
        "secondary_collection_rationale": values[
            "secondary_collection_rationale"
        ],
        "confidence": values["confidence"],
        "rationale": values["rationale"],
        "evidence_basis": values["evidence_basis"],
        "actor": actor,
        "decided_at": decided_at,
        "previous_status": previous_status,
        "new_status": new_status,
    }
    actions.append(action)
    candidate.update(
        {
            "current_status": new_status,
            "current_decision": values["decision"],
            "exclusion_reason_code": values["exclusion_reason_code"],
            "topic_code": values["topic_code"],
            "duplicate_target_id": values["duplicate_target_id"],
            "secondary_collection_code": values["secondary_collection_code"],
            "secondary_collection_rationale": values[
                "secondary_collection_rationale"
            ],
            "last_action_id": action_id,
            "updated_at": decided_at,
        }
    )
    write_table(curation / "review_queue.csv", queue_fields, queue)
    write_table(curation / "actions.csv", action_fields, actions)
    return action


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--issue-body-file", type=Path, required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--date", dest="decided_at", required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    action = apply_decision(
        args.root.resolve(),
        args.issue_body_file.read_text(encoding="utf-8"),
        args.actor,
        args.issue_number,
        args.decided_at,
    )
    if args.output:
        args.output.write_text(
            json.dumps(action, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"[OK] Recorded {action['decision']} for {action['candidate_id']} "
        f"as {action['action_id']}."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, json.JSONDecodeError, CandidateDecisionError) as exc:
        raise SystemExit(f"[CURATION BLOCKED] {exc}") from exc
