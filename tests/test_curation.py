from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.curation.apply_action import CurationError, Instruction, RegistryEditor


HEADERS = {
    "papers.csv": [
        "paper_id", "doi", "title", "title_normalised", "authors", "year",
        "venue", "publisher", "volume", "issue", "pages", "abstract",
        "language", "document_type", "canonical_status", "created_at", "updated_at",
    ],
    "work_identifiers.csv": [
        "identifier_id", "paper_id", "scheme", "value", "relation", "is_primary",
        "source", "verification_status", "verified_at",
    ],
    "discovery_events.csv": [
        "event_id", "paper_id", "execution_id", "feed_type", "source_name",
        "source_platform", "source_paper_id", "parent_paper_id", "query_id",
        "query_string", "rank", "retrieved_at", "retrieval_status", "raw_snapshot",
        "checksum", "notes",
    ],
    "screening_decisions.csv": [
        "decision_id", "paper_id", "execution_id", "screening_stage", "decision",
        "exclusion_reason_code", "exclusion_comment", "confidence", "reviewer",
        "decision_date", "is_current", "notes",
    ],
    "publications.csv": [
        "publication_id", "paper_id", "publication_version", "publication_status",
        "public_relevance_reason", "topic_code", "scope_fit", "metadata_confidence",
        "source_basis", "metadata_verified_at", "first_published_version", "is_current",
        "supersedes_publication_id", "version_note", "updated_at",
    ],
    "paper_codes.csv": [
        "coding_id", "paper_id", "dimension", "code", "coding_version",
        "evidence_quote", "coder", "coded_at", "is_current",
        "supersedes_coding_id", "notes",
    ],
    "taxonomy.csv": [
        "dimension", "code", "label", "definition", "parent_code", "taxonomy_version",
    ],
    "exclusion_reasons.csv": ["code", "label", "definition"],
    "work_relations.csv": [
        "relation_id", "source_paper_id", "target_paper_id", "relation", "reason",
        "evidence", "curator", "decided_at",
    ],
}


def row(**values: str) -> dict[str, str]:
    return values


class CuratorActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.registry = self.root / "data" / "registry"
        self.registry.mkdir(parents=True)
        tables = {
            "papers.csv": [
                row(
                    paper_id="P000001", doi="10.1234/one", title="First work",
                    title_normalised="first work", authors="Author, A.", year="2020",
                    venue="Journal", publisher="Publisher", volume="", issue="", pages="",
                    abstract="", language="en", document_type="journal_article",
                    canonical_status="review_included", created_at="2026-01-01",
                    updated_at="2026-01-01",
                ),
                row(
                    paper_id="P000002", doi="10.1234/two", title="Second record",
                    title_normalised="second record", authors="Author, A.", year="2020",
                    venue="Journal", publisher="Publisher", volume="", issue="", pages="",
                    abstract="", language="en", document_type="journal_article",
                    canonical_status="review_included", created_at="2026-01-01",
                    updated_at="2026-01-01",
                ),
            ],
            "work_identifiers.csv": [
                row(
                    identifier_id="ID000001", paper_id="P000001", scheme="doi",
                    value="10.1234/one", relation="canonical", is_primary="true",
                    source="fixture", verification_status="verified", verified_at="2026-01-01",
                ),
                row(
                    identifier_id="ID000002", paper_id="P000002", scheme="doi",
                    value="10.1234/two", relation="canonical", is_primary="true",
                    source="fixture", verification_status="verified", verified_at="2026-01-01",
                ),
            ],
            "discovery_events.csv": [
                self.event("EV000001", "P000001"),
                self.event("EV000002", "P000002"),
            ],
            "screening_decisions.csv": [
                self.decision("SD000001", "P000001"),
                self.decision("SD000002", "P000002"),
            ],
            "publications.csv": [
                self.publication("P000001", "alpha"),
                self.publication("P000002", "beta"),
            ],
            "paper_codes.csv": [
                row(
                    coding_id="PC000001", paper_id="P000001", dimension="topic",
                    code="alpha", coding_version="1", evidence_quote="Fixture A",
                    coder="fixture", coded_at="2026-01-01", is_current="true",
                    supersedes_coding_id="", notes="",
                ),
                row(
                    coding_id="PC000002", paper_id="P000002", dimension="topic",
                    code="beta", coding_version="1", evidence_quote="Fixture B",
                    coder="fixture", coded_at="2026-01-01", is_current="true",
                    supersedes_coding_id="", notes="",
                ),
            ],
            "taxonomy.csv": [
                row(
                    dimension="topic", code="alpha", label="Alpha", definition="First topic",
                    parent_code="", taxonomy_version="1.0",
                ),
                row(
                    dimension="topic", code="beta", label="Beta", definition="Second topic",
                    parent_code="", taxonomy_version="1.0",
                ),
            ],
            "exclusion_reasons.csv": [
                row(
                    code="TOPIC_OFF_SCOPE", label="Outside scope",
                    definition="The work is outside the review topic.",
                ),
                row(
                    code="DUPLICATE_RECORD", label="Duplicate",
                    definition="Another record represents the work.",
                ),
                row(
                    code="NOT_ACADEMIC_SOURCE", label="Not academic",
                    definition="The item is not an academic source.",
                ),
                row(
                    code="FULL_TEXT_UNAVAILABLE", label="Unavailable",
                    definition="The necessary full text is unavailable.",
                ),
            ],
            "work_relations.csv": [],
        }
        for name, rows in tables.items():
            self.write_csv(name, rows)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_csv(self, name: str, rows: list[dict[str, str]]) -> None:
        with (self.registry / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS[name], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def event(event_id: str, paper_id: str) -> dict[str, str]:
        return row(
            event_id=event_id, paper_id=paper_id, execution_id="E1", feed_type="fixture",
            source_name="Fixture", source_platform="fixture", source_paper_id="",
            parent_paper_id="", query_id="Q1", query_string="fixture", rank="1",
            retrieved_at="2026-01-01", retrieval_status="success", raw_snapshot="",
            checksum="", notes="",
        )

    @staticmethod
    def decision(decision_id: str, paper_id: str) -> dict[str, str]:
        return row(
            decision_id=decision_id, paper_id=paper_id, execution_id="E1",
            screening_stage="full_text", decision="eligible_core", exclusion_reason_code="",
            exclusion_comment="", confidence="high", reviewer="fixture",
            decision_date="2026-01-01", is_current="true", notes="",
        )

    @staticmethod
    def publication(paper_id: str, topic: str) -> dict[str, str]:
        numeric = paper_id.removeprefix("P")
        return row(
            publication_id=f"PUB{numeric}V001", paper_id=paper_id,
            publication_version="1", publication_status="published",
            public_relevance_reason="Fixture relevance.", topic_code=topic, scope_fit="direct",
            metadata_confidence="high", source_basis="Fixture", metadata_verified_at="2026-01-01",
            first_published_version="0.1.0", is_current="true",
            supersedes_publication_id="", version_note="Initial fixture.", updated_at="2026-01-01",
        )

    @staticmethod
    def instruction(operation: str, **overrides: str) -> Instruction:
        values = {
            "operation": operation,
            "paper_id": "P000001",
            "target_paper_id": "",
            "topic_code": "",
            "reason_code": "",
            "reason": "Evidence-backed curator reason.",
            "evidence": "Verified abstract and full-text section 2.",
            "confidence": "high",
            "actor": "owner",
            "action_date": "2026-01-02",
            "run_id": "test-1",
            "confirmation": "APPLY",
        }
        values.update(overrides)
        return Instruction(**values)

    def test_confirmation_failure_writes_nothing(self) -> None:
        before = {
            path.name: path.read_text(encoding="utf-8")
            for path in self.registry.glob("*.csv")
        }
        editor = RegistryEditor(self.root)
        with self.assertRaisesRegex(CurationError, "exactly"):
            editor.apply(
                self.instruction("exclude_work", confirmation="apply", reason_code="outside_scope")
            )
        after = {
            path.name: path.read_text(encoding="utf-8")
            for path in self.registry.glob("*.csv")
        }
        self.assertEqual(before, after)

    def test_change_topic_appends_publication_version_and_replaces_topic_code(self) -> None:
        editor = RegistryEditor(self.root)
        editor.apply(self.instruction("change_topic", topic_code="beta"))
        publications = editor.tables["publications.csv"]
        current = [row for row in publications if row["paper_id"] == "P000001" and row["is_current"] == "true"]
        self.assertEqual(1, len(current))
        self.assertEqual("2", current[0]["publication_version"])
        self.assertEqual("beta", current[0]["topic_code"])
        self.assertEqual("PUB000001V001", current[0]["supersedes_publication_id"])
        codes = [
            row
            for row in editor.tables["paper_codes.csv"]
            if row["paper_id"] == "P000001"
        ]
        self.assertEqual(2, len(codes))
        self.assertEqual("Fixture A", codes[0]["evidence_quote"])
        self.assertEqual("false", codes[0]["is_current"])
        self.assertEqual("beta", codes[1]["code"])
        self.assertEqual("2", codes[1]["coding_version"])
        self.assertEqual("true", codes[1]["is_current"])
        self.assertEqual("PC000001", codes[1]["supersedes_coding_id"])

    def test_exclude_work_preserves_history_and_withholds_current_version(self) -> None:
        editor = RegistryEditor(self.root)
        editor.apply(self.instruction("exclude_work", reason_code="TOPIC_OFF_SCOPE"))
        paper = next(row for row in editor.tables["papers.csv"] if row["paper_id"] == "P000001")
        self.assertEqual("review_excluded", paper["canonical_status"])
        decisions = [row for row in editor.tables["screening_decisions.csv"] if row["paper_id"] == "P000001"]
        self.assertEqual(2, len(decisions))
        current_decision = next(row for row in decisions if row["is_current"] == "true")
        self.assertEqual("not_eligible", current_decision["decision"])
        self.assertEqual("TOPIC_OFF_SCOPE", current_decision["exclusion_reason_code"])
        publications = [row for row in editor.tables["publications.csv"] if row["paper_id"] == "P000001"]
        self.assertEqual(2, len(publications))
        current_publication = next(row for row in publications if row["is_current"] == "true")
        self.assertEqual("withheld", current_publication["publication_status"])

    def test_exclude_work_rejects_an_invented_reason_code(self) -> None:
        editor = RegistryEditor(self.root)
        with self.assertRaisesRegex(CurationError, "Unknown exclusion reason code"):
            editor.apply(
                self.instruction("exclude_work", reason_code="outside_scope")
            )

    def test_source_reason_uses_the_matching_decision(self) -> None:
        editor = RegistryEditor(self.root)
        editor.apply(
            self.instruction("exclude_work", reason_code="NOT_ACADEMIC_SOURCE")
        )
        current = next(
            row for row in editor.tables["screening_decisions.csv"]
            if row["paper_id"] == "P000001" and row["is_current"] == "true"
        )
        self.assertEqual("not_academic", current["decision"])

    def test_merge_duplicate_moves_identity_and_keeps_retired_history(self) -> None:
        editor = RegistryEditor(self.root)
        editor.apply(
            self.instruction(
                "merge_duplicate", paper_id="P000002", target_paper_id="P000001"
            )
        )
        papers = {row["paper_id"]: row for row in editor.tables["papers.csv"]}
        self.assertEqual("superseded", papers["P000002"]["canonical_status"])
        self.assertEqual("", papers["P000002"]["doi"])
        moved = next(
            row for row in editor.tables["work_identifiers.csv"]
            if row["identifier_id"] == "ID000002"
        )
        self.assertEqual("P000001", moved["paper_id"])
        self.assertEqual("manifestation", moved["relation"])
        self.assertEqual("false", moved["is_primary"])
        self.assertTrue(all(
            row["paper_id"] == "P000001"
            for row in editor.tables["discovery_events.csv"]
        ))
        relation = editor.tables["work_relations.csv"][0]
        self.assertEqual("P000002", relation["source_paper_id"])
        self.assertEqual("P000001", relation["target_paper_id"])
        self.assertEqual("duplicate_of", relation["relation"])
        source_decisions = [
            row for row in editor.tables["screening_decisions.csv"]
            if row["paper_id"] == "P000002"
        ]
        self.assertEqual(2, len(source_decisions))
        self.assertEqual(
            "duplicate",
            next(row for row in source_decisions if row["is_current"] == "true")["decision"],
        )
        source_codes = [
            row for row in editor.tables["paper_codes.csv"]
            if row["paper_id"] == "P000002"
        ]
        self.assertEqual(1, len(source_codes))
        self.assertEqual("Fixture B", source_codes[0]["evidence_quote"])


if __name__ == "__main__":
    unittest.main()
