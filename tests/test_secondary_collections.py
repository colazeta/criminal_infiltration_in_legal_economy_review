from __future__ import annotations

import copy
import unittest

from scripts.build_secondary_collections import (
    SecondaryCollectionBuildError,
    build_records,
    current_secondary_publication_rows,
)


class SecondaryCollectionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.papers = [
            {
                "paper_id": "P000100",
                "doi": "10.1000/aml",
                "title": "A broader AML study",
                "authors": "Scholar, Ada",
                "year": "2025",
                "venue": "Journal of Financial Crime",
                "publisher": "Example Press",
                "volume": "1",
                "issue": "2",
                "pages": "1-20",
                "language": "en",
                "document_type": "journal_article",
                "canonical_status": "review_excluded",
            }
        ]
        self.events = [{"paper_id": "P000100"}]
        self.decisions = [
            {
                "paper_id": "P000100",
                "screening_stage": "full_text",
                "decision": "not_eligible",
                "exclusion_reason_code": "ADJACENT_PHENOMENON_ONLY",
                "is_current": "true",
            }
        ]
        self.core_publications = [
            {
                "paper_id": "P000100",
                "publication_status": "withheld",
                "is_current": "true",
            }
        ]
        self.identifiers = [
            {
                "paper_id": "P000100",
                "scheme": "doi",
                "value": "10.1000/aml",
                "is_primary": "true",
                "verification_status": "verified",
            }
        ]
        self.collections = [
            {
                "collection_code": "broader_aml",
                "label": "Anti-money laundering and economic/financial crime",
                "description": "Broader related scholarship.",
                "eligibility_relation": "outside_core_review",
            }
        ]
        self.secondary_publications = [
            {
                "secondary_publication_id": "SP000100V001",
                "paper_id": "P000100",
                "collection_code": "broader_aml",
                "publication_version": "1",
                "publication_status": "published",
                "public_relevance_reason": (
                    "Analyses a money-laundering mechanism outside the infiltration test."
                ),
                "metadata_confidence": "high",
                "source_basis": "Verified journal record",
                "metadata_verified_at": "2026-09-01",
                "first_published_version": "0.3.0",
                "is_current": "true",
                "supersedes_secondary_publication_id": "",
                "version_note": "Initial secondary publication.",
                "updated_at": "2026-09-01",
            }
        ]
        self.reasons = [
            {
                "code": "ADJACENT_PHENOMENON_ONLY",
                "label": "Adjacent phenomenon only",
            }
        ]

    def records(self):
        return build_records(
            copy.deepcopy(self.papers),
            copy.deepcopy(self.events),
            copy.deepcopy(self.decisions),
            copy.deepcopy(self.core_publications),
            copy.deepcopy(self.identifiers),
            copy.deepcopy(self.collections),
            copy.deepcopy(self.secondary_publications),
            copy.deepcopy(self.reasons),
        )

    def test_published_secondary_record_preserves_negative_core_decision(self) -> None:
        records = self.records()
        self.assertEqual(1, len(records))
        self.assertEqual("outside_core_review", records[0]["status"])
        self.assertEqual("not_eligible", records[0]["screeningDecision"])
        self.assertEqual("broader_aml", records[0]["collectionCode"])

    def test_routing_without_secondary_publication_approval_stays_hidden(self) -> None:
        self.secondary_publications[0]["publication_status"] = "withheld"
        self.assertEqual([], self.records())

    def test_eligible_work_cannot_leak_into_secondary_collection(self) -> None:
        self.decisions[0]["decision"] = "eligible_contextual"
        with self.assertRaisesRegex(
            SecondaryCollectionBuildError, "current decision is not not_eligible"
        ):
            self.records()

    def test_secondary_work_must_remain_withheld_from_core(self) -> None:
        self.core_publications[0]["publication_status"] = "published"
        with self.assertRaisesRegex(
            SecondaryCollectionBuildError, "core publication manifest is not withheld"
        ):
            self.records()

    def test_secondary_work_requires_verified_primary_identity(self) -> None:
        self.identifiers[0]["verification_status"] = "unverified"
        with self.assertRaisesRegex(
            SecondaryCollectionBuildError, "no verified primary identifier"
        ):
            self.records()

    def test_secondary_history_is_linear_and_versioned(self) -> None:
        first = self.secondary_publications[0]
        first["is_current"] = "false"
        second = copy.deepcopy(first)
        second.update(
            {
                "secondary_publication_id": "SP000100V002",
                "publication_version": "2",
                "is_current": "true",
                "supersedes_secondary_publication_id": "SP000100V001",
            }
        )
        current = current_secondary_publication_rows([first, second])
        self.assertEqual(["SP000100V002"], [row["secondary_publication_id"] for row in current])


if __name__ == "__main__":
    unittest.main()
