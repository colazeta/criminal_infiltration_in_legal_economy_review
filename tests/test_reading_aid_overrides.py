import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReadingAidOverrideTests(unittest.TestCase):
    def test_overrides_are_complete_and_non_decisional(self) -> None:
        payload = json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schemaVersion"], 1)
        records = payload["records"]
        self.assertTrue(records)
        ids = [record["candidateId"] for record in records]
        self.assertEqual(len(ids), len(set(ids)))
        for record in records:
            for field in ("candidateId", "kind", "sourceLabel", "sourceUrl", "synopsis", "checkedAt", "note"):
                self.assertTrue(str(record[field]).strip())
            self.assertTrue(record["sourceUrl"].startswith("https://"))
            self.assertNotIn("eligible_core", record["synopsis"])

    def test_targeted_retrieval_upgrades_known_hard_cases(self) -> None:
        records = {
            row["candidateId"]: row
            for row in json.loads((ROOT / "data/curation/reading_aid_overrides.json").read_text(encoding="utf-8"))["records"]
        }
        self.assertEqual(records["E0R1-C015"]["kind"], "publisher_summary")
        self.assertEqual(records["E0R1-C040"]["kind"], "publisher_summary")
        self.assertNotEqual(records["E0R1-C013"]["sourceLabel"], "DOI record requiring verification")


if __name__ == "__main__":
    unittest.main()
