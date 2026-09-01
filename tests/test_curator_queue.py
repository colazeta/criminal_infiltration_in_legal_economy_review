from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from scripts.curation.apply_candidate_decision import (
    CandidateDecisionError,
    apply_decision,
)
from scripts.curation.build_legacy_queue import materialise, render
from scripts.curation.build_curator_stats import build_payload as build_curator_stats
from scripts.curation.import_intake_issue import (
    IntakeImportError,
    import_candidates,
)
from scripts.curation.materialize_queue_issues import issue_body, reconcile_issue


ROOT = Path(__file__).resolve().parents[1]


def decision_body(
    candidate_id: str = "E0-D002",
    decision: str = "eligible_contextual",
    exclusion_reason: str = "NOT_APPLICABLE",
    topic_code: str = "conceptual_foundations",
    duplicate_target: str = "_No response_",
    secondary_collection: str = "NOT_APPLICABLE",
    secondary_collection_rationale: str = "_No response_",
    confirmation: str = "APPLY",
) -> str:
    sections = {
        "Candidate ID": candidate_id,
        "Screening stage": "full_text",
        "Decision": decision,
        "Exclusion reason": exclusion_reason,
        "Topic code": topic_code,
        "Duplicate target": duplicate_target,
        "Secondary collection": secondary_collection,
        "Secondary collection relevance": secondary_collection_rationale,
        "Confidence": "high",
        "Evidence basis and locator": "Full text, section 2, examined by the curator.",
        "Record-specific rationale": "The work provides a necessary conceptual contribution.",
        "Confirmation": confirmation,
    }
    return "\n\n".join(f"### {key}\n\n{value}" for key, value in sections.items())


def intake_body(
    *,
    batch_id: str = "ACADEMIC-2026-08-31",
    candidate_id: str = "CAND-ACADEMIC-2026-08-31-001",
    verification_status: str = "metadata_partial",
    metadata_conflict: str | None = "Year differs across source records.",
    sources: list[str] | None = None,
    query_ids: list[str] | None = None,
) -> str:
    sources = sources or ["Consensus", "Exa"]
    query_ids = query_ids or ["CONSENSUS-W1-Q1", "EXA-GAP-Q1"]
    search = {
        "schema_version": 1,
        "batch_id": batch_id,
        "repository_commit": "a" * 40,
        "sources": [
            {
                "source": "Consensus",
                "queries": [
                    {"query_id": "CONSENSUS-W1-Q1", "query_text": "mafia firms"}
                ],
            },
            {
                "source": "Exa",
                "queries": [
                    {"query_id": "EXA-GAP-Q1", "query_text": "criminal infiltration"}
                ],
            },
        ],
    }
    candidates = {
        "schema_version": 1,
        "batch_id": batch_id,
        "candidates": [
            {
                "candidate_id": candidate_id,
                "title": "A new candidate study",
                "authors": ["Ada Researcher", "Bruno Scholar"],
                "year": 2026,
                "venue": "Journal of Evidence",
                "work_type": "peer_reviewed",
                "identifiers": {"doi": "https://doi.org/10.1000/example", "other": []},
                "source_links": ["https://example.org/record"],
                "sources": sources,
                "query_ids": query_ids,
                "verification_status": verification_status,
                "possible_duplicate": "Compare with P000001.",
                "metadata_conflict": metadata_conflict,
                "intake_assessment": "plausible_core",
                "relevance_reason": "The title and metadata plausibly match the scope.",
                "required_human_action": "Resolve metadata and inspect the abstract.",
            }
        ],
    }
    safeguards = "\n".join(
        (
            "- [x] No candidate was marked eligible or published.",
            "- [x] Canonical records and existing intake issues were checked for duplicates.",
            "- [x] No copyrighted full text or long abstract is included.",
        )
    )
    return "\n\n".join(
        (
            f"### Batch ID\n\n{batch_id}",
            "### Search and provenance log\n\n```json\n"
            + json.dumps(search)
            + "\n```",
            "### Candidate records\n\n```json\n"
            + json.dumps(candidates)
            + "\n```",
            f"### Safeguards\n\n{safeguards}",
        )
    )


class LegacyQueueTests(unittest.TestCase):
    def test_materialises_expected_55_record_backlog(self) -> None:
        rows = materialise(ROOT)
        self.assertEqual(55, len(rows))
        self.assertEqual(
            Counter(
                {
                    "abstract_full_text_review": 25,
                    "legacy_rejection_review": 19,
                    "manual_review": 9,
                    "metadata_fix": 2,
                }
            ),
            Counter(row["review_stage"] for row in rows),
        )
        self.assertNotIn("E0-D001", {row["candidate_id"] for row in rows})
        self.assertNotIn("E0R1-C002", {row["candidate_id"] for row in rows})
        with (ROOT / "data/curation/review_queue.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            committed = [
                row
                for row in csv.DictReader(handle)
                if row["origin"].startswith("legacy_")
            ]
        self.assertEqual(render(committed), render(rows))

    def test_issue_payload_marks_legacy_signal_as_non_decision(self) -> None:
        row = materialise(ROOT)[0]
        body = issue_body(
            "colazeta/criminal_infiltration_in_legal_economy_review", row
        )
        body_flat = " ".join(body.split())
        self.assertIn(f"curator-candidate:{row['candidate_id']}", body)
        self.assertIn("Pilot provenance — not a decision", body)
        self.assertIn("It is not a governed eligibility decision", body_flat)
        self.assertIn(
            f"curate.html?candidate={row['candidate_id']}",
            body,
        )
        self.assertIn("temporary fallback", body_flat)
        self.assertNotIn("abstract", body.lower())

    def test_public_curator_projection_contains_aggregates_only(self) -> None:
        payload = build_curator_stats(ROOT)
        with (ROOT / "data/curation/review_queue.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            queue = list(csv.DictReader(handle))
        open_rows = [row for row in queue if row["current_status"] in {"pending", "needs_full_text"}]
        self.assertEqual(len(open_rows), payload["open"])
        self.assertEqual(len(queue) - len(open_rows), payload["completed"])
        self.assertEqual(
            Counter(
                "daily" if row["origin"] == "daily_surveillance" else "legacy"
                for row in open_rows
            ),
            Counter(payload["openByOrigin"]),
        )
        self.assertEqual({"broaderAml": 0}, payload["bySecondaryCollection"])
        rendered = json.dumps(payload).lower()
        for forbidden in ("candidate_id", "title", "doi", "actor", "rationale"):
            self.assertNotIn(forbidden, rendered)


class CandidateDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "data/curation").mkdir(parents=True)
        (self.root / "data/registry").mkdir(parents=True)
        for relative in (
            "data/curation/review_queue.csv",
            "data/curation/actions.csv",
            "data/registry/papers.csv",
            "data/registry/taxonomy.csv",
            "data/registry/exclusion_reasons.csv",
            "data/registry/secondary_collections.csv",
        ):
            source = ROOT / relative
            target = self.root / relative
            shutil.copyfile(source, target)
        self.registry_before = {
            path.name: path.read_text(encoding="utf-8")
            for path in (self.root / "data/registry").glob("*.csv")
        }
        self.open_before = build_curator_stats(self.root)["open"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def rows(self, relative: str) -> list[dict[str, str]]:
        with (self.root / relative).open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    def test_eligible_decision_updates_queue_and_appends_action_only(self) -> None:
        action = apply_decision(
            self.root,
            decision_body(),
            "colazeta",
            "101",
            "2026-08-31",
        )
        self.assertEqual("eligible_contextual", action["decision"])
        candidate = next(
            row
            for row in self.rows("data/curation/review_queue.csv")
            if row["candidate_id"] == "E0-D002"
        )
        self.assertEqual("screened_eligible_contextual", candidate["current_status"])
        self.assertEqual("conceptual_foundations", candidate["topic_code"])
        self.assertEqual(1, len(self.rows("data/curation/actions.csv")))
        public_stats = build_curator_stats(self.root)
        self.assertEqual(self.open_before - 1, public_stats["open"])
        self.assertEqual(1, public_stats["completed"])
        self.assertEqual(1, public_stats["actionCount"])
        registry_after = {
            path.name: path.read_text(encoding="utf-8")
            for path in (self.root / "data/registry").glob("*.csv")
        }
        self.assertEqual(self.registry_before, registry_after)

    def test_non_eligible_decision_requires_governed_reason(self) -> None:
        with self.assertRaisesRegex(
            CandidateDecisionError, "governed exclusion reason"
        ):
            apply_decision(
                self.root,
                decision_body(
                    decision="not_eligible",
                    exclusion_reason="NOT_APPLICABLE",
                    topic_code="_No response_",
                ),
                "colazeta",
                "102",
                "2026-08-31",
            )

    def test_non_eligible_candidate_can_be_routed_to_broader_aml(self) -> None:
        action = apply_decision(
            self.root,
            decision_body(
                decision="not_eligible",
                exclusion_reason="ADJACENT_PHENOMENON_ONLY",
                topic_code="_No response_",
                secondary_collection="broader_aml",
                secondary_collection_rationale=(
                    "The work substantively analyses a laundering mechanism."
                ),
            ),
            "colazeta",
            "106",
            "2026-09-01",
        )
        self.assertEqual("not_eligible", action["decision"])
        self.assertEqual("broader_aml", action["secondary_collection_code"])
        candidate = next(
            row
            for row in self.rows("data/curation/review_queue.csv")
            if row["candidate_id"] == "E0-D002"
        )
        self.assertEqual("screened_not_eligible", candidate["current_status"])
        self.assertEqual("broader_aml", candidate["secondary_collection_code"])
        public_stats = build_curator_stats(self.root)
        self.assertEqual(1, public_stats["bySecondaryCollection"]["broaderAml"])

    def test_secondary_collection_requires_not_eligible_and_rationale(self) -> None:
        with self.assertRaisesRegex(CandidateDecisionError, "only with not_eligible"):
            apply_decision(
                self.root,
                decision_body(
                    secondary_collection="broader_aml",
                    secondary_collection_rationale="Adjacent AML contribution.",
                ),
                "colazeta",
                "107",
                "2026-09-01",
            )
        with self.assertRaisesRegex(
            CandidateDecisionError, "secondary collection relevance"
        ):
            apply_decision(
                self.root,
                decision_body(
                    decision="not_eligible",
                    exclusion_reason="ADJACENT_PHENOMENON_ONLY",
                    topic_code="_No response_",
                    secondary_collection="broader_aml",
                ),
                "colazeta",
                "108",
                "2026-09-01",
            )

    def test_duplicate_requires_known_distinct_target(self) -> None:
        action = apply_decision(
            self.root,
            decision_body(
                decision="duplicate",
                exclusion_reason="DUPLICATE_RECORD",
                topic_code="_No response_",
                duplicate_target="P000002",
            ),
            "colazeta",
            "103",
            "2026-08-31",
        )
        self.assertEqual("P000002", action["duplicate_target_id"])
        self.assertEqual("duplicate_confirmed", action["new_status"])

    def test_one_decision_issue_cannot_be_applied_twice(self) -> None:
        body = decision_body()
        apply_decision(self.root, body, "colazeta", "104", "2026-08-31")
        with self.assertRaisesRegex(CandidateDecisionError, "already produced"):
            apply_decision(self.root, body, "colazeta", "104", "2026-08-31")

    def test_confirmation_is_literal(self) -> None:
        with self.assertRaisesRegex(CandidateDecisionError, "exactly"):
            apply_decision(
                self.root,
                decision_body(confirmation="apply"),
                "colazeta",
                "105",
                "2026-08-31",
            )


class DailyIntakeQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "data/curation").mkdir(parents=True)
        shutil.copyfile(
            ROOT / "data/curation/review_queue.csv",
            self.root / "data/curation/review_queue.csv",
        )
        self.queue_before = len(self.rows())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def rows(self) -> list[dict[str, str]]:
        with (self.root / "data/curation/review_queue.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            return list(csv.DictReader(handle))

    def test_validated_daily_intake_is_staged_without_a_decision(self) -> None:
        result = import_candidates(
            self.root,
            intake_body(),
            "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
            "201",
            "2026-08-31",
        )
        self.assertEqual(1, len(result["added"]))
        self.assertEqual(self.queue_before + 1, result["queue_total"])
        row = next(
            row
            for row in self.rows()
            if row["candidate_id"] == "CAND-ACADEMIC-2026-08-31-001"
        )
        self.assertEqual("daily_surveillance", row["origin"])
        self.assertEqual("metadata_fix", row["review_stage"])
        self.assertEqual("pending", row["current_status"])
        self.assertEqual("", row["current_decision"])
        self.assertEqual("Compare with P000001.", row["possible_duplicate"])
        self.assertEqual(
            "Resolve metadata and inspect the abstract.",
            row["required_human_action"],
        )
        body = issue_body(
            "colazeta/criminal_infiltration_in_legal_economy_review", row
        )
        self.assertIn("Daily intake provenance — not a decision", body)
        self.assertIn("Required human action", body)
        self.assertIn("https://example.org/record", body)
        self.assertNotIn("marked eligible", body)

    def test_verified_daily_intake_goes_to_evidence_review(self) -> None:
        import_candidates(
            self.root,
            intake_body(
                verification_status="metadata_verified",
                metadata_conflict=None,
            ),
            "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
            "202",
            "2026-08-31",
        )
        row = next(row for row in self.rows() if row["origin"] == "daily_surveillance")
        self.assertEqual("abstract_full_text_review", row["review_stage"])

    def test_duplicate_import_is_blocked(self) -> None:
        values = (
            self.root,
            intake_body(),
            "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
            "203",
            "2026-08-31",
        )
        import_candidates(*values)
        with self.assertRaisesRegex(IntakeImportError, "already materialised"):
            import_candidates(*values)

    def test_second_issue_for_same_batch_is_blocked(self) -> None:
        import_candidates(
            self.root,
            intake_body(),
            "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
            "206",
            "2026-08-31",
        )
        with self.assertRaisesRegex(IntakeImportError, "already staged"):
            import_candidates(
                self.root,
                intake_body(candidate_id="CAND-ACADEMIC-2026-08-31-002"),
                "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
                "207",
                "2026-08-31",
            )

    def test_issue_title_must_match_manifest_batch(self) -> None:
        with self.assertRaisesRegex(IntakeImportError, "title disagrees"):
            import_candidates(
                self.root,
                intake_body(),
                "[INTAKE][ACADEMIC] ACADEMIC-2026-08-30",
                "204",
                "2026-08-31",
            )

    def test_candidate_queries_must_match_named_sources(self) -> None:
        with self.assertRaisesRegex(IntakeImportError, "disagrees with sources"):
            import_candidates(
                self.root,
                intake_body(sources=["Consensus"]),
                "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
                "205",
                "2026-08-31",
            )

    def test_all_intake_safeguards_must_be_checked(self) -> None:
        body = intake_body().replace(
            "- [x] No candidate was marked eligible or published.",
            "- [ ] No candidate was marked eligible or published.",
        )
        with self.assertRaisesRegex(IntakeImportError, "check exactly once"):
            import_candidates(
                self.root,
                body,
                "[INTAKE][ACADEMIC] ACADEMIC-2026-08-31",
                "208",
                "2026-08-31",
            )


class QueueIssueReconciliationTests(unittest.TestCase):
    @patch("scripts.curation.materialize_queue_issues.api_request")
    def test_existing_queue_issue_receives_curator_workspace_link(
        self, api_mock
    ) -> None:
        row = materialise(ROOT)[0]
        current_body = """<!-- curator-candidate:E0-D002 -->

## Candidate record

Verifier-corrected metadata that is not yet in the queue table.

## Curator action

Old action link.

## Verifier notes

Preserve this manually authored note.
"""
        writes = reconcile_issue(
            "colazeta/criminal_infiltration_in_legal_economy_review",
            "token",
            row,
            {
                "number": 299,
                "state": "open",
                "labels": [
                    {"name": "curation:queue"},
                    {"name": "stage:manual-review"},
                ],
                "body": current_body,
            },
            {},
        )
        self.assertEqual(1, writes)
        call = api_mock.call_args
        self.assertEqual("PATCH", call.args[2])
        self.assertIn("curate.html?candidate=", call.args[4]["body"])
        self.assertIn("temporary fallback", " ".join(call.args[4]["body"].split()))
        self.assertIn("Verifier-corrected metadata", call.args[4]["body"])
        self.assertIn("Preserve this manually authored note", call.args[4]["body"])
        self.assertNotIn("Old action link", call.args[4]["body"])

    @patch("scripts.curation.materialize_queue_issues.api_request")
    @patch("scripts.curation.materialize_queue_issues.paginated", return_value=[])
    def test_completed_candidate_issue_is_linked_and_closed(
        self, paginated_mock, api_mock
    ) -> None:
        row = next(
            dict(candidate)
            for candidate in materialise(ROOT)
            if candidate["candidate_id"] == "E0-D002"
        )
        row.update(
            {
                "current_status": "screened_not_eligible",
                "last_action_id": "CA000001",
            }
        )
        actions = {
            "CA000001": {
                "action_id": "CA000001",
                "github_issue_number": "301",
                "decision": "not_eligible",
            }
        }
        writes = reconcile_issue(
            "colazeta/criminal_infiltration_in_legal_economy_review",
            "token",
            row,
            {
                "number": 300,
                "state": "open",
                "labels": [],
                "body": issue_body(
                    "colazeta/criminal_infiltration_in_legal_economy_review",
                    row,
                ),
            },
            actions,
        )
        self.assertEqual(2, writes)
        paginated_mock.assert_called_once()
        calls = api_mock.call_args_list
        self.assertEqual("POST", calls[0].args[2])
        self.assertIn("curator-action:CA000001", calls[0].args[4]["body"])
        self.assertEqual("PATCH", calls[1].args[2])
        self.assertEqual(
            {"state": "closed", "state_reason": "completed"},
            calls[1].args[4],
        )

    @patch("scripts.curation.materialize_queue_issues.paginated", return_value=[])
    @patch("scripts.curation.materialize_queue_issues.api_request")
    def test_routed_candidate_issue_receives_secondary_collection_label(
        self, api_mock, paginated_mock
    ) -> None:
        row = next(
            dict(candidate)
            for candidate in materialise(ROOT)
            if candidate["candidate_id"] == "E0-D002"
        )
        row.update(
            {
                "current_status": "screened_not_eligible",
                "secondary_collection_code": "broader_aml",
                "last_action_id": "CA000002",
            }
        )
        actions = {
            "CA000002": {
                "action_id": "CA000002",
                "candidate_id": "E0-D002",
                "github_issue_number": "302",
                "decision": "not_eligible",
                "secondary_collection_code": "broader_aml",
            }
        }
        writes = reconcile_issue(
            "colazeta/criminal_infiltration_in_legal_economy_review",
            "token",
            row,
            {
                "number": 300,
                "state": "closed",
                "labels": [{"name": "curation:queue"}],
                "body": issue_body(
                    "colazeta/criminal_infiltration_in_legal_economy_review",
                    row,
                ),
            },
            actions,
        )
        self.assertEqual(2, writes)
        self.assertEqual("POST", api_mock.call_args_list[0].args[2])
        self.assertIn("broader_aml", api_mock.call_args_list[0].args[4]["body"])
        self.assertEqual(
            {"labels": ["collection:broader-aml"]},
            api_mock.call_args_list[1].args[4],
        )


if __name__ == "__main__":
    unittest.main()
