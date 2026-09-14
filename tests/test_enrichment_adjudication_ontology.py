import json
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EnrichmentAdjudicationOntologyTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ROOT / "ontology/cile-review-profile.yaml").read_text())
        self.module = json.loads((ROOT / "ontology/modules/enrichment-adjudication.json").read_text())
        self.public = json.loads((ROOT / "ontology/modules/public-enrichment-completion.json").read_text())

    def valid_target(self, target):
        if target in self.profile["slots"]:
            return True
        return ":" in target and target.split(":", 1)[0] in self.profile["prefixes"]

    def test_private_receipt_tables_are_fully_mapped_and_append_only(self):
        self.assertEqual(self.module["profile_version"], self.profile["version"])
        connection = sqlite3.connect(":memory:")
        for migration in self.module["migrations"]:
            connection.executescript((ROOT / migration).read_text())
        for table, contract in self.module["tables"].items():
            self.assertIn(contract["class"], self.profile["classes"])
            fields = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
            self.assertEqual(fields, set(contract["fields"]))
            self.assertTrue(all(self.valid_target(target) for target in contract["fields"].values()))
            for action in ("update", "delete"):
                trigger = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
                    (f"{table}_no_{action}",),
                ).fetchone()
                self.assertIsNotNone(trigger)
        connection.close()

    def test_public_completion_schema_is_closed_and_fully_mapped(self):
        schema = json.loads((ROOT / self.public["schema"]).read_text())
        fields = set()

        def visit(spec, pointer=""):
            if "properties" in spec:
                self.assertFalse(spec.get("additionalProperties", True), pointer)
                self.assertEqual(set(spec.get("required", [])), set(spec["properties"]), pointer)
                for name, child in spec["properties"].items():
                    path = f"{pointer}/properties/{name}"
                    fields.add(path)
                    visit(child, path)
            if "items" in spec and isinstance(spec["items"], dict):
                visit(spec["items"], pointer + "/items")

        visit(schema)
        self.assertEqual(fields, set(self.public["schema_field_slots"]))
        self.assertTrue(all(self.valid_target(target) for target in self.public["schema_field_slots"].values()))
        self.assertEqual(schema["properties"]["completed"]["type"], "boolean")
        self.assertNotIn("human_login", schema["properties"])
        self.assertNotIn("receipt_id", schema["properties"])
        self.assertNotIn("source_snapshot_sha256", schema["properties"])


if __name__ == "__main__":
    unittest.main()
