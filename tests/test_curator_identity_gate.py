from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CuratorIdentityGateTests(unittest.TestCase):
    def test_identity_resolution_is_explicit_and_non_decisional(self) -> None:
        javascript = (ROOT / "site/curator-resolved-link.js").read_text(encoding="utf-8")
        self.assertIn("Identity-resolution and guided-decision layer", javascript)
        self.assertIn('metadata_repair: "Metadati da riparare"', javascript)
        self.assertIn('manifestation_ambiguity: "Manifestazione da risolvere"', javascript)
        self.assertIn('duplicate_risk: "Rischio duplicato"', javascript)
        self.assertIn("Diagnostica preparatoria", javascript)
        self.assertIn("blocksScreening", javascript)
        self.assertNotIn('select.value = "eligible_core"', javascript)
        self.assertNotIn('select.value = "duplicate"', javascript)

    def test_metadata_gate_blocks_scientific_submit_but_duplicate_signal_does_not_decide(self) -> None:
        javascript = (ROOT / "site/curator-resolved-link.js").read_text(encoding="utf-8")
        self.assertIn('state === "metadata_repair"', javascript)
        self.assertIn('state === "manifestation_ambiguity"', javascript)
        self.assertIn("submit.disabled = currentIdentity.blocksScreening", javascript)
        self.assertIn('currentIdentity?.state === "duplicate_risk"', javascript)
        self.assertIn("nessun esito è preselezionato", javascript)

    def test_guided_decisions_preserve_governed_select_values(self) -> None:
        javascript = (ROOT / "site/curator-resolved-link.js").read_text(encoding="utf-8")
        for decision in (
            "eligible_core",
            "eligible_contextual",
            "maybe_full_text_needed",
            "not_eligible",
            "duplicate",
            "not_academic",
            "not_retrievable",
        ):
            self.assertIn(decision, javascript)
        self.assertIn('select.dispatchEvent(new Event("change", { bubbles: true }))', javascript)
        self.assertIn("Gestione record eccezionale", javascript)
        self.assertIn("Le card impostano il medesimo valore governato", javascript)


if __name__ == "__main__":
    unittest.main()
