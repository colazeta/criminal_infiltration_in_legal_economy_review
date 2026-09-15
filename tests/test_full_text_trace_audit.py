from __future__ import annotations

import unittest

from scripts.calibration.full_text_trace_audit import AUDIT_PROTOCOL, summarise_synthesis


class FullTextTraceAuditTests(unittest.TestCase):
    def test_valid_graph_has_no_failure_family(self) -> None:
        synthesis = {
            "studies": [{"id": "s1"}],
            "datasets": [{"id": "d1", "study_id": "s1"}],
            "analyses": [{"id": "a1", "study_id": "s1", "dataset_ids": ["d1"]}],
            "variable_uses": [{"id": "v1", "analysis_id": "a1", "dataset_ids": ["d1"]}],
            "findings": [{"id": "f1", "analysis_id": "a1", "variable_use_ids": ["v1"]}],
        }
        summary = summarise_synthesis(synthesis)
        self.assertEqual(summary["protocol"], AUDIT_PROTOCOL)
        self.assertEqual(summary["relation_failures"], {})
        self.assertEqual(summary["failure_families"], [])
        self.assertEqual(summary["record_counts"]["variable_uses"], 1)

    def test_relation_failures_are_counts_without_record_ids(self) -> None:
        synthesis = {
            "studies": [{"id": "secret-study"}],
            "datasets": [{"id": "secret-dataset", "study_id": "secret-study"}],
            "analyses": [{"id": "secret-analysis", "study_id": "secret-study", "dataset_ids": ["missing-dataset", "missing-dataset"]}],
            "variable_uses": [{"id": "secret-variable", "analysis_id": "missing-analysis", "dataset_ids": ["secret-dataset"]}],
            "findings": [{"id": "secret-finding", "analysis_id": "secret-analysis", "variable_use_ids": ["secret-variable"]}],
        }
        summary = summarise_synthesis(synthesis)
        self.assertEqual(summary["relation_failures"]["analysis_missing_dataset"], 2)
        self.assertEqual(summary["relation_failures"]["analysis_duplicate_dataset_ref"], 1)
        self.assertEqual(summary["relation_failures"]["variable_missing_analysis"], 1)
        rendered = str(summary)
        for secret in ("secret-study", "secret-dataset", "secret-analysis", "secret-variable", "secret-finding"):
            self.assertNotIn(secret, rendered)

    def test_cross_analysis_finding_is_detected(self) -> None:
        synthesis = {
            "studies": [{"id": "s1"}],
            "datasets": [{"id": "d1", "study_id": "s1"}],
            "analyses": [
                {"id": "a1", "study_id": "s1", "dataset_ids": ["d1"]},
                {"id": "a2", "study_id": "s1", "dataset_ids": ["d1"]},
            ],
            "variable_uses": [{"id": "v1", "analysis_id": "a1", "dataset_ids": ["d1"]}],
            "findings": [{"id": "f1", "analysis_id": "a2", "variable_use_ids": ["v1"]}],
        }
        summary = summarise_synthesis(synthesis)
        self.assertEqual(summary["relation_failures"]["finding_variable_analysis_mismatch"], 1)


if __name__ == "__main__":
    unittest.main()
