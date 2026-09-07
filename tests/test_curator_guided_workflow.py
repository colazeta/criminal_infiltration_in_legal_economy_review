from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CuratorGuidedWorkflowTests(unittest.TestCase):
    def source(self) -> str:
        return (ROOT / "site/curator-config.js").read_text(encoding="utf-8")

    def test_guided_flow_has_three_explicit_steps(self) -> None:
        source = self.source()
        self.assertIn('CILE-GUIDED-v1', source)
        self.assertIn('1 · VALUTAZIONE', source)
        self.assertIn('2 · PUNTO CRITICO', source)
        self.assertIn('3 · DECISIONE', source)
        self.assertIn('PASSO ${currentStep} DI 3', source)
        self.assertIn('criticalPoint(data)', source)
        self.assertIn('CONTROARGOMENTO PIÙ FORTE', source)
        self.assertIn('COSA MI FAREBBE CAMBIARE IDEA', source)

    def test_assistant_precedes_evidence_and_form_in_operating_path(self) -> None:
        source = self.source()
        self.assertIn('metadata.insertAdjacentElement("afterend", panel)', source)
        self.assertIn('assist-guided-ready:not([data-assist-evidence-open="true"]) #candidate-abstract-panel', source)
        self.assertIn('assist-guided-ready[data-assist-flow="guided"] #decision-form', source)
        self.assertIn('MOSTRA EVIDENZA', source)
        self.assertIn('NASCONDI EVIDENZA', source)
        self.assertIn('detail.dataset.assistFlow = "guided"', source)

    def test_accept_edit_and_deepen_are_separate_human_actions(self) -> None:
        source = self.source()
        self.assertIn('ACCETTA E PREPARA', source)
        self.assertIn('MODIFICA', source)
        self.assertIn('APPROFONDISCI', source)
        self.assertIn('const sourceApply = byId("assist-apply")', source)
        self.assertIn('sourceApply.click()', source)
        self.assertIn('const sourceDeepen = byId("assist-deepen")', source)
        self.assertIn('sourceDeepen.click()', source)
        self.assertNotIn('/api/decisions', source)
        self.assertNotIn('explicit-confirmation', source)
        self.assertNotIn('decision-form").submit', source)

    def test_identity_gate_blocks_acceptance(self) -> None:
        source = self.source()
        self.assertIn('data.blocked || !data.proposalReady', source)
        self.assertIn('NON POSSO PREPARARE LA DECISIONE', source)
        self.assertIn('GATE APERTO', source)

    def test_guided_layer_does_not_add_network_work(self) -> None:
        source = self.source()
        guided = source[source.index('// Guided operating layer.'):]
        self.assertNotIn('fetch(', guided)
        self.assertNotIn('/api/free-web-search', guided)
        self.assertNotIn('/api/enrichment', guided)
        self.assertNotIn('/api/resolved-abstract', guided)
        self.assertIn('sourceDeepen.click()', guided)

    def test_observer_ignores_its_own_render_mutations(self) -> None:
        source = self.source()
        self.assertIn('onlyGuidedMutations', source)
        self.assertIn('mutations.every((mutation) => guided.contains(mutation.target))', source)
        self.assertIn('if (!onlyGuidedMutations) queueRender()', source)

    def test_visual_contract_remains_classic_and_flat(self) -> None:
        source = self.source()
        guided = source[source.index('style.textContent = `'):]
        self.assertIn('background:#000080', guided)
        self.assertIn('background:#d4d0c8', guided)
        self.assertIn('border-radius:0', guided)
        self.assertIn('box-shadow:none', guided)
        self.assertNotIn('linear-gradient', guided)
        self.assertNotIn('border-radius:999', guided)
        self.assertNotIn('transition:', guided)


if __name__ == "__main__":
    unittest.main()
