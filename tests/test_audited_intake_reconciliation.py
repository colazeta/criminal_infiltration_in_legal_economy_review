from __future__ import annotations

import copy
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.curation import audited_intake_reconciliation as audit
from scripts.curation.import_intake_issue import IntakeImportError
from scripts.curation.recover_intake_backlog import reconcile_terminal_absent_issue

ROOT = Path(__file__).resolve().parents[1]


def rows():
    return [
        dict(zip(audit.IDENTITY_FIELDS, [
            "CAND-ACADEMIC-2026-09-13-EXTRA-a6766e6649ed-004",
            "Organized Crime and the Legal Economy", "", "", "UNICRI", "", "",
            "https://unicri.org/sites/default/files/2021-06/UNICRI_Organized_Crime_and_Legal_Economy_report.pdf",
        ])),
        dict(zip(audit.IDENTITY_FIELDS, [
            "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-024",
            "Social welfare fraud and criminal infiltration in Sweden",
            "Johanna Skinnari; Lars Korsell; Helena Rönnblom", "2016",
            "Organised Crime in European Businesses", "", "",
            "https://www.routledge.com/Organised-Crime-in-European-Businesses/Savona-Riccardi-Berlusconi/p/book/9781138499478",
        ])),
    ]


class AuditedOccurrenceTests(unittest.TestCase):
    def setUp(self):
        self.issue = {"number": 225, "title": f"[INTAKE][ACADEMIC] {audit.BATCH}",
                      "user": {"login": "colazeta"}, "body": "synthetic test evidence"}
        self.candidates = [{"candidate_id": key} for key in audit.AUDITED_OCCURRENCES]
        self.pin = patch.object(audit, "SOURCE_BODY_SHA256",
                                hashlib.sha256(self.issue["body"].encode()).hexdigest())
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def test_exact_targets_reconcile_without_mutating_input(self):
        queue = rows()
        before = copy.deepcopy((self.issue, queue, self.candidates))
        remaining, skipped = audit.audited_occurrences(self.issue, queue, self.candidates)
        self.assertEqual(remaining, [])
        self.assertEqual(len(skipped), 2)
        self.assertEqual((self.issue, queue, self.candidates), before)
        self.assertTrue(all(row["matched_keys"][1].startswith("https://") for row in skipped))

    def test_unreviewed_issue_gets_no_exception(self):
        self.issue["number"] = 226
        self.assertEqual(audit.audited_occurrences(self.issue, rows(), self.candidates),
                         (self.candidates, []))

    def test_wrong_owner_fails_closed(self):
        self.issue["user"]["login"] = "other"
        with self.assertRaisesRegex(IntakeImportError, "owner"):
            audit.audited_occurrences(self.issue, rows(), self.candidates)

    def test_changed_source_or_title_fails_closed(self):
        for field in ("body", "title"):
            changed = copy.deepcopy(self.issue)
            changed[field] += " "
            with self.subTest(field=field), self.assertRaises(IntakeImportError):
                audit.audited_occurrences(changed, rows(), self.candidates)

    def test_missing_or_duplicated_target_fails_closed(self):
        for queue in (rows()[1:], rows() + [rows()[0]]):
            with self.subTest(queue=queue), self.assertRaises(IntakeImportError):
                audit.audited_occurrences(self.issue, queue, self.candidates)

    def test_changed_bibliographic_fields_fail_closed(self):
        for field in audit.IDENTITY_FIELDS:
            queue = rows()
            queue[0][field] += "altered"
            with self.subTest(field=field), self.assertRaises(IntakeImportError):
                audit.audited_occurrences(self.issue, queue, self.candidates)

    def test_nonidentity_enrichment_does_not_change_identity(self):
        queue = rows()
        queue[0]["retrieval_note"] = "Not an identity field"
        self.assertEqual(len(audit.audited_occurrences(self.issue, queue, self.candidates)[1]), 2)

    def test_residual_article_is_not_whitelisted_away(self):
        residual = {"candidate_id": f"CAND-{audit.BATCH}-003"}
        remaining, skipped = audit.audited_occurrences(self.issue, rows(), self.candidates + [residual])
        self.assertEqual(remaining, [residual])
        self.assertEqual(len(skipped), 2)

    def test_terminal_absent_intake_cannot_create_residual_article(self):
        residual = {"candidate_id": f"CAND-{audit.BATCH}-003",
                    "title": "A residual unrepresented article", "authors": [], "year": 2020,
                    "identifiers": {"doi": "10.1177/1477370818803050", "other": []}}
        manifest = {"batch_id": audit.BATCH, "candidates": self.candidates + [residual]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue_path = root / "data/curation/review_queue.csv"
            queue_path.parent.mkdir(parents=True)
            with queue_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=audit.IDENTITY_FIELDS)
                writer.writeheader(); writer.writerows(rows())
            before = queue_path.read_bytes()
            with patch("scripts.curation.recover_intake_backlog.parse_intake_issue", return_value=manifest):
                with self.assertRaisesRegex(IntakeImportError, "003"):
                    reconcile_terminal_absent_issue(root, self.issue, "colazeta")
            self.assertEqual(queue_path.read_bytes(), before)
            self.assertFalse((root / "data/curation/intake_access").exists())

    def test_target_fingerprints_match_reviewed_values(self):
        for row, (_, expected, _) in zip(rows(), audit.AUDITED_OCCURRENCES.values()):
            self.assertEqual(audit.identity_fingerprint(row), expected)


class MaintenanceRetriggerTests(unittest.TestCase):
    def test_command_is_exact_owner_only_and_canonical_issue_only(self):
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        self.assertIn("github.event.issue.number == 362", workflow)
        self.assertIn("github.event.comment.body == '/recover-intake'", workflow)
        self.assertIn("github.event.comment.user.login == github.repository_owner", workflow)
        self.assertIn("github.event.issue.user.login == github.repository_owner", workflow)
        self.assertIn("github.actor == github.repository_owner", workflow)
        self.assertIn("queue: max", workflow)
        self.assertIn("cancel-in-progress: false", workflow)

    def test_receipt_survives_failure_and_comment_trigger_is_reported(self):
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        self.assertIn("Retain candidate-conservation receipt\n        if: always()", workflow)
        self.assertIn('"$EVENT_NAME" = "issue_comment"', workflow)
        self.assertIn('"$TRIGGER_TITLE" = "[MAINTENANCE][INTAKE-RECOVERY]"', workflow)


if __name__ == "__main__":
    unittest.main()
