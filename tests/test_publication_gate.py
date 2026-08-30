from __future__ import annotations

import copy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_archive import (  # noqa: E402
    PUBLIC_RECORD_FIELDS,
    ArchiveBuildError,
    build_payload,
    build_records,
)


class PublicationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.papers = [
            {
                "paper_id": "P1",
                "doi": "10.1234/example",
                "title": "Example work",
                "authors": "Author, A.",
                "year": "2024",
                "venue": "Journal",
                "publisher": "Publisher",
                "volume": "1",
                "issue": "2",
                "pages": "1-9",
                "language": "en",
                "document_type": "journal_article",
                "canonical_status": "seed_included",
            }
        ]
        self.events = [{"event_id": "EV1", "paper_id": "P1"}]
        self.decisions = [
            {
                "decision_id": "SD1",
                "paper_id": "P1",
                "decision": "eligible_core",
                "screening_stage": "title_abstract",
                "is_current": "true",
            }
        ]
        self.publications = [
            {
                "paper_id": "P1",
                "publication_status": "published",
                "public_relevance_reason": "Directly analyses the review construct.",
                "topic_code": "topic",
                "scope_fit": "direct",
                "metadata_confidence": "high",
                "source_basis": "Verified source",
                "metadata_verified_at": "2026-01-01",
            }
        ]
        self.identifiers = [
            {
                "identifier_id": "ID1",
                "paper_id": "P1",
                "scheme": "doi",
                "value": "10.1234/example",
                "is_primary": "true",
                "verification_status": "verified",
            }
        ]
        self.topics = {"topic": "Topic"}

    def records(self):
        return build_records(
            copy.deepcopy(self.papers),
            copy.deepcopy(self.events),
            copy.deepcopy(self.decisions),
            copy.deepcopy(self.publications),
            copy.deepcopy(self.identifiers),
            copy.deepcopy(self.topics),
        )

    def test_valid_record_is_published_with_exact_allowlist(self) -> None:
        records = self.records()
        self.assertEqual(["P1"], [record["id"] for record in records])
        self.assertEqual(PUBLIC_RECORD_FIELDS, tuple(records[0]))

    def test_withheld_record_is_not_published(self) -> None:
        self.publications[0]["publication_status"] = "withheld"
        self.assertEqual([], self.records())

    def test_current_pending_decision_fails_closed(self) -> None:
        self.decisions[0]["decision"] = "maybe_full_text_needed"
        with self.assertRaisesRegex(ArchiveBuildError, "not eligible"):
            self.records()

    def test_historical_eligible_current_excluded_fails_closed(self) -> None:
        self.decisions[0]["is_current"] = "false"
        self.decisions.append(
            {
                "decision_id": "SD2",
                "paper_id": "P1",
                "decision": "not_eligible",
                "screening_stage": "full_text",
                "is_current": "true",
            }
        )
        with self.assertRaisesRegex(ArchiveBuildError, "not eligible"):
            self.records()

    def test_superseded_record_fails_closed(self) -> None:
        self.papers[0]["canonical_status"] = "superseded"
        with self.assertRaisesRegex(ArchiveBuildError, "canonical status"):
            self.records()

    def test_missing_event_fails_closed(self) -> None:
        self.events = []
        with self.assertRaisesRegex(ArchiveBuildError, "no discovery event"):
            self.records()

    def test_zero_or_two_current_decisions_fail_closed(self) -> None:
        self.decisions[0]["is_current"] = "false"
        with self.assertRaisesRegex(ArchiveBuildError, "found 0"):
            self.records()
        self.decisions[0]["is_current"] = "true"
        self.decisions.append(copy.deepcopy(self.decisions[0]))
        with self.assertRaisesRegex(ArchiveBuildError, "found 2"):
            self.records()

    def test_blank_public_reason_fails_closed(self) -> None:
        self.publications[0]["public_relevance_reason"] = ""
        with self.assertRaisesRegex(ArchiveBuildError, "public_relevance_reason"):
            self.records()

    def test_legacy_or_raw_files_cannot_change_payload(self) -> None:
        expected = build_payload(ROOT)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            shutil.copytree(ROOT / "data/registry", temp_root / "data/registry")
            (temp_root / "data/raw").mkdir(parents=True)
            (temp_root / "data/raw/candidate.csv").write_text(
                "paper_id,public_relevance_reason\nP000001,MALICIOUS\n",
                encoding="utf-8",
            )
            (temp_root / "data/legacy").mkdir(parents=True)
            (temp_root / "data/legacy/audit.csv").write_text(
                "rejected_omitted\n999999\n", encoding="utf-8"
            )
            self.assertEqual(expected, build_payload(temp_root))


if __name__ == "__main__":
    unittest.main()
