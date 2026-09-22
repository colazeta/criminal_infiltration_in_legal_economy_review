from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/metrics"))
sys.path.insert(0, str(ROOT))

from surveillance import MetricsError, build_public_payload, validate_public_payload, validate_run
from fetch_surveillance_ledger import verify_search_manifest
from test_surveillance_metrics import REPOSITORY, exa_run


def parallel_run(day="2026-09-10"):
    run = exa_run(day)
    run["schema_version"] = 3
    run["expected_sources"] = ["Parallel Search"]
    run["sources"][0]["source"] = "Parallel Search"
    run["notes"] = ["Parallel Search selected as the scheduled default provider."]
    return run


def search_section(run):
    manifest = {
        "schema_version": 3,
        "batch_id": run["batch_id"],
        "repository_commit": run["repository_commit"],
        "sources": [{
            "source": "Parallel Search",
            "queries": [
                {"query_id": f"PARALLEL-W{i}-Q1", "query_text": f"Synthetic fallback W{i}"}
                for i in range(1, 8)
            ],
        }],
    }
    return "```json\n" + json.dumps(manifest) + "\n```"


class ParallelSearchProviderTests(unittest.TestCase):
    def test_parallel_search_is_valid_without_exa_fallback_note(self):
        run = parallel_run()
        validated = validate_run(run)
        self.assertEqual(["Parallel Search"], validated["expected_sources"])

    def test_legacy_exa_fallback_note_remains_valid(self):
        run = parallel_run()
        run["notes"] = [
            "Exa fallback: credit limit after a failed optional Exa attempt; final W1-W7 used Parallel Search."
        ]
        self.assertEqual(["Parallel Search"], validate_run(run)["expected_sources"])

    def test_parallel_search_final_provider_is_valid_and_has_scoped_queries(self):
        run = validate_run(parallel_run())
        query_sources = verify_search_manifest(run, search_section(run))
        self.assertEqual({"Parallel Search"}, set(query_sources.values()))
        self.assertIn("PARALLEL-W7-Q1", query_sources)

    def test_parallel_query_cannot_use_exa_prefix(self):
        run = validate_run(parallel_run())
        section = search_section(run).replace("PARALLEL-W4-Q1", "EXA-W4-Q1")
        with self.assertRaisesRegex(MetricsError, "source-scoped ID"):
            verify_search_manifest(run, section)

    def test_public_stats_can_span_exa_and_parallel_completed_days(self):
        primary = exa_run("2026-09-09")
        primary["schema_version"] = 3
        fallback = parallel_run("2026-09-10")
        payload = build_public_payload([primary, fallback], 30, REPOSITORY)
        validate_public_payload(payload)
        self.assertEqual(["Exa", "Parallel Search"], [row["source"] for row in payload["sources"]])
        self.assertEqual(2, sum(row["expectedRuns"] for row in payload["sources"]))

    def test_v2_remains_exa_only(self):
        run = exa_run("2026-09-09")
        run["expected_sources"] = ["Parallel Search"]
        run["sources"][0]["source"] = "Parallel Search"
        with self.assertRaisesRegex(MetricsError, "governed active source set"):
            validate_run(run)


if __name__ == "__main__":
    unittest.main()
