#!/usr/bin/env python3
"""Apply one explicit owner-curator instruction to the governed registries.

The script never infers an operation. It requires a literal confirmation, keeps
decision and publication history, and is intended to run in a temporary Git
branch before a visible pull request is created.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


OPERATIONS = {"change_topic", "exclude_work", "merge_duplicate"}
ACTIVE_TARGET_STATUSES = {"seed_included", "review_included", "review_pending"}
REGISTRY_FILES = (
    "papers.csv",
    "work_identifiers.csv",
    "discovery_events.csv",
    "screening_decisions.csv",
    "publications.csv",
    "paper_codes.csv",
    "taxonomy.csv",
    "exclusion_reasons.csv",
    "work_relations.csv",
)


class CurationError(ValueError):
    """Raised when a curator instruction is incomplete or unsafe to apply."""


@dataclass(frozen=True)
class Instruction:
    operation: str
    paper_id: str
    target_paper_id: str
    topic_code: str
    reason_code: str
    reason: str
    evidence: str
    confidence: str
    actor: str
    action_date: str
    run_id: str
    confirmation: str


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CurationError(f"{path.name} has no header")
        if any(not (field or "").strip() for field in reader.fieldnames):
            raise CurationError(f"{path.name} has a blank header column")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise CurationError(f"{path.name} has duplicate header columns")
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise CurationError(
                    f"{path.name}:{line_number} has more values than header columns"
                )
            if any(value is None for value in row.values()):
                raise CurationError(
                    f"{path.name}:{line_number} has fewer values than header columns"
                )
            rows.append(dict(row))
        return list(reader.fieldnames), rows


def write_table(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def require_text(value: str, label: str, maximum: int = 2000) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise CurationError(f"{label} is required")
    if len(cleaned) > maximum:
        raise CurationError(f"{label} exceeds {maximum} characters")
    return cleaned


def require_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise CurationError("action date must use YYYY-MM-DD") from exc


def next_identifier(rows: list[dict[str, str]], field: str, prefix: str) -> str:
    numbers: list[int] = []
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    for row in rows:
        match = pattern.fullmatch((row.get(field) or "").strip())
        if match:
            numbers.append(int(match.group(1)))
    return f"{prefix}{max(numbers, default=0) + 1:06d}"


def paper_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {(row.get("paper_id") or "").strip(): row for row in rows}


def current_rows(
    rows: list[dict[str, str]], paper_id: str
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("paper_id") == paper_id
        and (row.get("is_current") or "").strip().lower() == "true"
    ]


def publication_id(paper_id: str, version: int) -> str:
    numeric = paper_id.removeprefix("P")
    if not numeric.isdigit():
        raise CurationError(f"Unsupported paper ID format: {paper_id}")
    return f"PUB{numeric}V{version:03d}"


class RegistryEditor:
    def __init__(self, root: Path):
        self.root = root
        self.registry = root / "data" / "registry"
        self.fields: dict[str, list[str]] = {}
        self.tables: dict[str, list[dict[str, str]]] = {}
        for name in REGISTRY_FILES:
            fields, rows = read_table(self.registry / name)
            self.fields[name] = fields
            self.tables[name] = rows

    def require_paper(self, paper_id: str) -> dict[str, str]:
        if not re.fullmatch(r"P\d{6}", paper_id):
            raise CurationError(f"Invalid paper ID format: {paper_id}")
        paper = paper_map(self.tables["papers.csv"]).get(paper_id)
        if not paper:
            raise CurationError(f"Unknown paper ID: {paper_id}")
        return paper

    def require_active_paper(self, paper_id: str) -> dict[str, str]:
        paper = self.require_paper(paper_id)
        if paper.get("canonical_status") not in ACTIVE_TARGET_STATUSES:
            raise CurationError(
                f"{paper_id} is not an active canonical record"
            )
        return paper

    def append_publication(
        self,
        paper_id: str,
        action_date: str,
        version_note: str,
        overrides: dict[str, str] | None = None,
    ) -> dict[str, str] | None:
        rows = self.tables["publications.csv"]
        current = current_rows(rows, paper_id)
        if not current:
            return None
        if len(current) != 1:
            raise CurationError(
                f"{paper_id} has {len(current)} current publication rows"
            )
        previous = current[0]
        previous["is_current"] = "false"
        version = int(previous["publication_version"]) + 1
        new_row = dict(previous)
        new_row.update(overrides or {})
        new_row.update(
            {
                "publication_id": publication_id(paper_id, version),
                "publication_version": str(version),
                "is_current": "true",
                "supersedes_publication_id": previous["publication_id"],
                "version_note": version_note,
                "updated_at": action_date,
            }
        )
        if any(row["publication_id"] == new_row["publication_id"] for row in rows):
            raise CurationError(
                f"Generated publication ID already exists: {new_row['publication_id']}"
            )
        rows.insert(rows.index(previous) + 1, new_row)
        return new_row

    def append_decision(
        self,
        paper_id: str,
        instruction: Instruction,
        decision: str,
        exclusion_reason_code: str,
        exclusion_comment: str,
        notes: str,
    ) -> dict[str, str]:
        rows = self.tables["screening_decisions.csv"]
        current = current_rows(rows, paper_id)
        if len(current) > 1:
            raise CurationError(f"{paper_id} has several current decisions")
        insert_at = rows.index(current[0]) + 1 if current else len(rows)
        for row in current:
            row["is_current"] = "false"
        new_row = {
            "decision_id": next_identifier(rows, "decision_id", "SD"),
            "paper_id": paper_id,
            "execution_id": f"CUR-{instruction.run_id}",
            "screening_stage": "curator_review",
            "decision": decision,
            "exclusion_reason_code": exclusion_reason_code,
            "exclusion_comment": exclusion_comment,
            "confidence": instruction.confidence,
            "reviewer": instruction.actor,
            "decision_date": instruction.action_date,
            "is_current": "true",
            "notes": notes,
        }
        rows.insert(insert_at, new_row)
        return new_row

    def change_topic(self, instruction: Instruction) -> None:
        self.require_active_paper(instruction.paper_id)
        topic = require_text(instruction.topic_code, "topic code", 100)
        valid_topics = {
            row["code"]
            for row in self.tables["taxonomy.csv"]
            if row.get("dimension") == "topic"
        }
        if topic not in valid_topics:
            raise CurationError(
                f"Unknown topic code {topic!r}; add it to taxonomy first if needed"
            )
        reason = require_text(instruction.reason, "reason")
        evidence = require_text(instruction.evidence, "evidence basis")
        publication = self.append_publication(
            instruction.paper_id,
            instruction.action_date,
            f"Owner curator changed the primary topic to {topic}: {reason}",
            {"topic_code": topic},
        )
        if publication is None:
            raise CurationError(
                f"{instruction.paper_id} has no publication history to classify"
            )

        codes = self.tables["paper_codes.csv"]
        history = [
            row
            for row in codes
            if row.get("paper_id") == instruction.paper_id
            and row.get("dimension") == "topic"
        ]
        current = [
            row
            for row in history
            if (row.get("is_current") or "").strip().lower() == "true"
        ]
        if len(current) > 1 or (history and len(current) != 1):
            raise CurationError(
                f"{instruction.paper_id} has an invalid current topic-code history"
            )
        previous = current[0] if current else None
        if previous:
            previous["is_current"] = "false"
        version = max(
            (int(row["coding_version"]) for row in history),
            default=0,
        ) + 1
        new_code = {
            "coding_id": next_identifier(codes, "coding_id", "PC"),
            "paper_id": instruction.paper_id,
            "dimension": "topic",
            "code": topic,
            "coding_version": str(version),
            "evidence_quote": evidence,
            "coder": instruction.actor,
            "coded_at": instruction.action_date,
            "is_current": "true",
            "supersedes_coding_id": previous["coding_id"] if previous else "",
            "notes": reason,
        }
        if previous:
            codes.insert(codes.index(previous) + 1, new_code)
        else:
            codes.append(new_code)

    def exclude_work(self, instruction: Instruction) -> None:
        paper = self.require_active_paper(instruction.paper_id)
        reason_code = require_text(instruction.reason_code, "exclusion reason code", 100)
        valid_reason_codes = {
            row["code"] for row in self.tables["exclusion_reasons.csv"]
        }
        if reason_code not in valid_reason_codes:
            raise CurationError(
                f"Unknown exclusion reason code: {reason_code}"
            )
        if reason_code == "DUPLICATE_RECORD":
            raise CurationError(
                "Use merge_duplicate when another canonical record represents the work"
            )
        reason = require_text(instruction.reason, "reason")
        evidence = require_text(instruction.evidence, "evidence basis")
        decision = {
            "NOT_ACADEMIC_SOURCE": "not_academic",
            "FULL_TEXT_UNAVAILABLE": "not_retrievable",
        }.get(reason_code, "not_eligible")
        paper["canonical_status"] = "review_excluded"
        paper["updated_at"] = instruction.action_date
        self.append_decision(
            instruction.paper_id,
            instruction,
            decision,
            reason_code,
            reason,
            f"Owner-curator action {instruction.run_id}. Evidence basis: {evidence}",
        )
        publication = self.append_publication(
            instruction.paper_id,
            instruction.action_date,
            f"Withheld after owner-curator exclusion ({reason_code}): {reason}",
            {
                "publication_status": "withheld",
                "public_relevance_reason": "",
                "topic_code": "",
                "scope_fit": "",
            },
        )
        if publication is None:
            raise CurationError(
                f"{instruction.paper_id} has no publication history to withhold"
            )

    def merge_duplicate(self, instruction: Instruction) -> None:
        source = self.require_active_paper(instruction.paper_id)
        target_id = require_text(
            instruction.target_paper_id, "surviving target paper ID", 30
        )
        target = self.require_active_paper(target_id)
        if instruction.paper_id == target_id:
            raise CurationError("Source and target paper IDs must differ")
        reason = require_text(instruction.reason, "reason")
        evidence = require_text(instruction.evidence, "identity evidence")
        relations = self.tables["work_relations.csv"]
        if any(
            row.get("source_paper_id") == instruction.paper_id
            for row in relations
        ):
            raise CurationError(
                f"{instruction.paper_id} already has a recorded work relation"
            )

        source["canonical_status"] = "superseded"
        source["doi"] = ""
        source["updated_at"] = instruction.action_date
        target["updated_at"] = instruction.action_date

        identifiers = self.tables["work_identifiers.csv"]
        target_has_primary_doi = any(
            row.get("paper_id") == target_id
            and row.get("scheme") == "doi"
            and row.get("is_primary") == "true"
            for row in identifiers
        )
        for row in identifiers:
            if row.get("paper_id") != instruction.paper_id:
                continue
            row["paper_id"] = target_id
            row["relation"] = "manifestation"
            if row.get("scheme") == "doi" and row.get("is_primary") == "true":
                if target_has_primary_doi:
                    row["is_primary"] = "false"
                else:
                    row["relation"] = "canonical"
                    target["doi"] = row["value"]
                    target_has_primary_doi = True

        for row in self.tables["discovery_events.csv"]:
            if row.get("paper_id") == instruction.paper_id:
                row["paper_id"] = target_id

        self.append_decision(
            instruction.paper_id,
            instruction,
            "duplicate",
            "DUPLICATE_RECORD",
            f"Duplicate of {target_id}: {reason}",
            f"Owner-curator action {instruction.run_id}. Identity evidence: {evidence}",
        )
        publication = self.append_publication(
            instruction.paper_id,
            instruction.action_date,
            f"Withheld because this record was merged into {target_id}: {reason}",
            {
                "publication_status": "withheld",
                "public_relevance_reason": "",
                "topic_code": "",
                "scope_fit": "",
            },
        )
        if publication is None:
            raise CurationError(
                f"{instruction.paper_id} has no publication history to merge"
            )
        relations.append(
            {
                "relation_id": next_identifier(
                    relations, "relation_id", "REL"
                ),
                "source_paper_id": instruction.paper_id,
                "target_paper_id": target_id,
                "relation": "duplicate_of",
                "reason": reason,
                "evidence": evidence,
                "curator": instruction.actor,
                "decided_at": instruction.action_date,
            }
        )

    def apply(self, instruction: Instruction) -> None:
        if instruction.confirmation != "APPLY":
            raise CurationError('confirmation must be exactly "APPLY"')
        if instruction.operation not in OPERATIONS:
            raise CurationError(f"Unsupported operation: {instruction.operation}")
        if instruction.confidence not in {"low", "medium", "high"}:
            raise CurationError("confidence must be low, medium or high")
        require_text(instruction.paper_id, "paper ID", 30)
        require_text(instruction.actor, "curator identity", 100)
        require_text(instruction.run_id, "run ID", 100)
        require_date(instruction.action_date)
        if instruction.operation == "change_topic":
            self.change_topic(instruction)
        elif instruction.operation == "exclude_work":
            self.exclude_work(instruction)
        else:
            self.merge_duplicate(instruction)

    def write(self) -> None:
        for name in REGISTRY_FILES:
            write_table(
                self.registry / name, self.fields[name], self.tables[name]
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root; defaults to the current repository",
    )
    parser.add_argument("--operation", required=True, choices=sorted(OPERATIONS))
    parser.add_argument("--paper-id", required=True)
    parser.add_argument("--target-paper-id", default="")
    parser.add_argument("--topic-code", default="")
    parser.add_argument("--reason-code", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--confidence", default="high")
    parser.add_argument("--actor", required=True)
    parser.add_argument("--date", dest="action_date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--confirm", dest="confirmation", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    instruction = Instruction(
        operation=args.operation,
        paper_id=args.paper_id.strip(),
        target_paper_id=args.target_paper_id.strip(),
        topic_code=args.topic_code.strip(),
        reason_code=args.reason_code.strip(),
        reason=args.reason.strip(),
        evidence=args.evidence.strip(),
        confidence=args.confidence.strip(),
        actor=args.actor.strip(),
        action_date=args.action_date.strip(),
        run_id=args.run_id.strip(),
        confirmation=args.confirmation,
    )
    try:
        editor = RegistryEditor(args.root.resolve())
        editor.apply(instruction)
        editor.write()
    except CurationError as exc:
        raise SystemExit(f"[CURATION BLOCKED] {exc}") from exc
    print(
        f"[OK] Prepared {instruction.operation} for {instruction.paper_id} "
        f"as curator {instruction.actor}."
    )


if __name__ == "__main__":
    main()
