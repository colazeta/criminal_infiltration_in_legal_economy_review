from __future__ import annotations

import unittest

from scripts.curation.sync_issue_candidate_record import desired_labels, replace_queue_identity


REPOSITORY = "colazeta/criminal_infiltration_in_legal_economy_review"


def candidate_row(**overrides: str) -> dict[str, str]:
    row = {
        "candidate_id": "CAND-ACADEMIC-2026-09-01-002",
        "title": "Testing the reliability of OSINT network data for investigating organised crime infiltration of legal-market businesses",
        "doi": "10.1080/17440572.2025.2567277",
        "authors": "Niles Breuer",
        "year": "2025",
        "venue": "Global Crime",
        "source": "Consensus",
        "review_stage": "abstract_full_text_review",
        "origin": "daily_surveillance",
        "intake_assessment": "plausible_core",
        "verification_status": "metadata_verified",
        "possible_duplicate": "",
        "metadata_conflict": "",
        "intake_reason": "Compares business-register networks with police data for a group infiltrating legal-market firms.",
        "required_human_action": "Assess identity, network construction, and evidence scope.",
        "source_query_id": "CONSENSUS-W1-Q1; CONSENSUS-W3-Q1; CONSENSUS-W5-Q1",
        "source_links": "https://example.test/intake; https://doi.org/10.1080/17440572.2025.2567277",
        "provenance": "github-issue:#89;batch:ACADEMIC-2026-09-01",
        "current_status": "pending",
        "current_decision": "",
        "last_action_id": "",
        "secondary_collection_code": "",
    }
    row.update(overrides)
    return row


class SyncIssueCandidateRecordTests(unittest.TestCase):
    def test_refreshes_primary_metadata_and_preserves_mechanical_sections(self) -> None:
        stale = """<!-- curator-candidate:CAND-ACADEMIC-2026-09-01-002 -->

## Candidate record

| Field | Value |
|---|---|
| Candidate ID | `CAND-ACADEMIC-2026-09-01-002` |
| Title | Testing the reliability of OSINT network data for investigating organised crime infiltration of legal-market businesses |
| Authors | Niles Breuer |
| Year | 2025 |
| Venue | Global Crime |
| DOI | Not recorded |
| Source | Consensus |
| Current review stage | **Metadata repair** |

## Daily intake provenance — not a decision

- Intake assessment: `plausible_core`
- Verification status: `metadata_partial`
- Possible duplicate note: none
- Metadata conflict: none
- Intake reason: old
- Required human action: old
- Query IDs: `CONSENSUS-W1-Q1`
- Source link 1: <https://example.test/intake>
- Provenance: `github-issue:#89;batch:ACADEMIC-2026-09-01`

The intake assessment and verification label above are retained only for triage and audit.

## Access status — mechanical

- Access status: `open`
- Last checked: `2026-09-02`

## Abstract coverage — mechanical

- Coverage status: `available`
- Last checked: `2026-09-02`

## Retrieval coverage — mechanical

- Resolution status: `full_text`
- Last checked: `2026-09-05`

## Curator action

Keep this exact curator action text.
"""
        mechanical_suffix = stale[stale.index("## Access status — mechanical") :].rstrip()
        updated = replace_queue_identity(stale, REPOSITORY, candidate_row())
        self.assertIn("[10.1080/17440572.2025.2567277]", updated)
        self.assertIn("Current review stage | **Abstract / full-text review**", updated)
        self.assertIn("Verification status: `metadata_verified`", updated)
        self.assertNotIn("| DOI | Not recorded |", updated)
        self.assertNotIn("Verification status: `metadata_partial`", updated)
        self.assertEqual(updated[updated.index("## Access status — mechanical") :].rstrip(), mechanical_suffix)

    def test_replaces_stage_label_and_preserves_non_stage_labels(self) -> None:
        issue = {
            "labels": [
                {"name": "curation:queue"},
                {"name": "stage:metadata-fix"},
                {"name": "collection:broader-aml"},
            ]
        }
        labels = desired_labels(issue, candidate_row())
        self.assertEqual(
            labels,
            ["curation:queue", "collection:broader-aml", "stage:abstract-review"],
        )
        self.assertNotIn("stage:metadata-fix", labels)

    def test_identity_sync_does_not_introduce_scientific_decisions(self) -> None:
        row = candidate_row()
        updated = replace_queue_identity(
            """<!-- curator-candidate:CAND-ACADEMIC-2026-09-01-002 -->

## Candidate record

stale

## Curator action

Existing action.
""",
            REPOSITORY,
            row,
        )
        self.assertIn("Intake assessment: `plausible_core`", updated)
        self.assertIn("not a governed eligibility decision", updated)
        self.assertNotIn("eligible_core", updated)
        self.assertNotIn("not_eligible", updated)
        self.assertNotIn("published", updated.lower())


if __name__ == "__main__":
    unittest.main()
