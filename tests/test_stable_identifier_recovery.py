from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.curation.recover_intake_backlog import reconcile_candidates_stable_first


FIELDS = ["candidate_id", "title", "doi", "authors", "year", "other_identifiers"]


class StableIdentifierRecoveryTests(unittest.TestCase):
    def test_exact_doi_reconciles_title_variant_without_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue = [
                {
                    "candidate_id": "CAND-OLD-001",
                    "title": "Evaluating risks-based communities of Mafia companies: a complex networks perspective",
                    "doi": "10.1007/s11156-021-00984-3",
                    "authors": "Nicola Giuseppe Castellano; Roy Cerqueti; Bruno Maria Franceschetti",
                    "year": "2021",
                    "other_identifiers": "",
                }
            ]
            candidate = {
                "candidate_id": "CAND-NEW-001",
                "title": "Evaluating risks-based communities of Mafia companies",
                "authors": [],
                "year": None,
                "identifiers": {
                    "doi": "10.1007/s11156-021-00984-3",
                    "other": [],
                },
            }
            novel, skipped = reconcile_candidates_stable_first(root, queue, [candidate])
            self.assertEqual(novel, [])
            self.assertEqual(len(skipped), 1)
            self.assertTrue(skipped[0]["title_variant"])
            self.assertIn("doi:10.1007/s11156-021-00984-3", skipped[0]["matched_keys"])
            self.assertEqual(skipped[0]["existing_ids"], ["candidate:CAND-OLD-001"])

    def test_nonmatching_stable_id_remains_novel(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            queue = [
                {
                    "candidate_id": "CAND-OLD-001",
                    "title": "Existing work",
                    "doi": "10.1000/existing",
                    "authors": "",
                    "year": "2020",
                    "other_identifiers": "",
                }
            ]
            candidate = {
                "candidate_id": "CAND-NEW-001",
                "title": "New work",
                "authors": [],
                "year": 2024,
                "identifiers": {"doi": "10.1000/new", "other": []},
            }
            novel, skipped = reconcile_candidates_stable_first(root, queue, [candidate])
            self.assertEqual([row["candidate_id"] for row in novel], ["CAND-NEW-001"])
            self.assertEqual(skipped, [])


if __name__ == "__main__":
    unittest.main()
