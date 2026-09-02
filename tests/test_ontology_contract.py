from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ontology" / "validate_ontology.py"
SPEC = importlib.util.spec_from_file_location("validate_ontology", MODULE_PATH)
assert SPEC and SPEC.loader
ontology = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ontology)


class OntologyContractTests(unittest.TestCase):
    def test_entire_governed_repository_conforms(self) -> None:
        result = ontology.validate_all(quiet=True)
        self.assertEqual(result["profile_version"], "0.1.0")
        self.assertGreaterEqual(result["governed_artifacts"], 20)
        self.assertGreaterEqual(result["candidates"], 68)

    def test_profile_reuses_external_ontologies_instead_of_reinventing_them(self) -> None:
        profile = json.loads((ROOT / "ontology/cile-review-profile.yaml").read_text(encoding="utf-8"))
        prefixes = profile["prefixes"]
        for prefix in ("slr", "prov", "fabio", "bibo", "oa", "skos", "ripe"):
            self.assertIn(prefix, prefixes)
        self.assertEqual(profile["classes"]["HumanAgent"]["class_uri"], "foaf:Person")
        self.assertEqual(profile["classes"]["EvidenceSpan"]["class_uri"], "oa:Annotation")
        self.assertIn("slr:IncludedSource", profile["classes"]["ScholarlyWork"]["exact_mappings"])

    def test_work_and_manifestation_are_distinct_semantic_classes(self) -> None:
        profile = json.loads((ROOT / "ontology/cile-review-profile.yaml").read_text(encoding="utf-8"))
        self.assertIn("ScholarlyWork", profile["classes"])
        self.assertIn("Manifestation", profile["classes"])
        self.assertNotEqual(
            profile["classes"]["ScholarlyWork"]["class_uri"],
            profile["classes"]["Manifestation"]["class_uri"],
        )
        contracts = json.loads((ROOT / "ontology/mappings/artifact-contracts.json").read_text(encoding="utf-8"))
        self.assertEqual(contracts["artifacts"]["data/registry/papers.csv"]["row_classes"], ["ScholarlyWork"])
        self.assertIn("Manifestation", contracts["artifacts"]["data/curation/retrieval_coverage.csv"]["row_classes"])

    def test_new_governed_csv_requires_an_ontology_contract(self) -> None:
        contracts = json.loads((ROOT / "ontology/mappings/artifact-contracts.json").read_text(encoding="utf-8"))
        declared = set(contracts["artifacts"])
        discovered = set()
        for root_name in contracts["governed_roots"]:
            discovered.update(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / root_name).glob("*.csv")
            )
        self.assertEqual(discovered, declared)


if __name__ == "__main__":
    unittest.main()
