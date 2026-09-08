from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CuratorMetadataConsensusTests(unittest.TestCase):
    def test_consensus_surface_reuses_enrichment_response(self) -> None:
        source = (ROOT / "site/curator-consensus.js").read_text(encoding="utf-8")
        self.assertIn("const originalFetch = window.fetch.bind(window)", source)
        self.assertIn('url.pathname === "/api/enrichment"', source)
        self.assertIn("response.clone().json()", source)
        self.assertIn("payload?.metadataResolution", source)
        self.assertNotIn("innerHTML", source)

    def test_consensus_exposes_field_support_and_manifestation_conflicts(self) -> None:
        source = (ROOT / "site/curator-consensus.js").read_text(encoding="utf-8")
        for marker in [
            "Concordanza bibliografica",
            "candidate-consensus-fields",
            "Supporto:",
            "Alternative:",
            "manifestation_ambiguity",
            "scholarIdentityBlocked",
        ]:
            self.assertIn(marker, source)

    def test_consensus_blocks_submit_but_never_chooses_scientific_outcome(self) -> None:
        source = (ROOT / "site/curator-consensus.js").read_text(encoding="utf-8")
        self.assertIn('event.target?.id !== "decision-form"', source)
        self.assertIn("event.stopImmediatePropagation()", source)
        self.assertIn("choice.disabled = true", source)
        for forbidden in [
            'value = "eligible_core"',
            'value = "eligible_contextual"',
            'value = "not_eligible"',
            'value = "duplicate"',
        ]:
            self.assertNotIn(forbidden, source)

    def test_e2_e3_is_explicit_user_action(self) -> None:
        source = (ROOT / "site/curator-consensus.js").read_text(encoding="utf-8")
        self.assertIn("Costruisci E2/E3", source)
        self.assertIn('target.searchParams.set("citations", "1")', source)
        self.assertIn("OpenCitations + Semantic Scholar", source)
        self.assertNotIn('searchParams.set("citations", "1");\n  window.fetch', source)

    def test_consensus_loads_before_reading_without_duplicate_api_call(self) -> None:
        config = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertLess(config.index("./curator-consensus.js"), config.index("./curator-reading.js"))
        self.assertIn("script.async = false", config)
        self.assertIn('"/curator-consensus.js"', worker)
        self.assertLess(worker.index("./curator-consensus.js"), worker.index("./curator-reading.js"))
        self.assertIn("script.async = false", worker)


if __name__ == "__main__":
    unittest.main()
