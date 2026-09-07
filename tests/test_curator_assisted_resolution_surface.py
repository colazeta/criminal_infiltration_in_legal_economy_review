from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CuratorAssistedResolutionSurfaceTests(unittest.TestCase):
    def test_surface_exposes_all_controlled_resolution_states(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("candidate-assisted-resolution-panel", source)
        self.assertIn("full_text_or_intro_ready", source)
        self.assertIn("publisher_summary_ready", source)
        self.assertIn("metadata_only", source)
        self.assertIn("known_noise", source)
        self.assertIn("not_verified_after_targeted_search", source)
        self.assertIn("not_applicable_noise", source)
        self.assertNotIn("innerHTML", source)

    def test_surface_consumes_same_origin_candidate_context_without_github_fetch(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn('document.addEventListener("curator:candidate-context"', source)
        self.assertIn("event?.detail?.context", source)
        self.assertIn("assistedResolution", source)
        self.assertIn("reviewSupport", source)
        self.assertNotIn("api.github.com", source)
        self.assertNotIn("localStorage", source)

    def test_decision_assist_is_reasoned_and_four_part(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        for marker in (
            "candidate-decision-assist-panel",
            "ASSISTENZA SCREENING",
            "GIUDIZIO DELL’ASSISTENTE",
            "MOTIVO DECISIVO",
            "ALTERNATIVA PIÙ PLAUSIBILE",
            "COSA MI FAREBBE CAMBIARE IDEA",
            "EVIDENZA UTILIZZATA",
            "LETTURA SOSTANZIALE",
            "assist-four-part-test",
            "Attore/interesse criminale identificabile",
            "Entità o contesto dell’economia legale",
            "Relazione sostenuta: accesso/partecipazione/influenza/controllo/embeddedness",
            "Analisi sostanziale della relazione",
        ):
            self.assertIn(marker, source)

    def test_assist_can_recommend_but_never_submits_or_confirms(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("APPLICA AL FORM", source)
        self.assertIn("function applyRecommendation()", source)
        self.assertIn('setField("decision", recommendation.decision)', source)
        self.assertIn('setField("confidence", recommendation.confidence)', source)
        self.assertIn('setField("evidence-basis", recommendation.evidenceBasis)', source)
        self.assertIn('setField("decision-rationale", rationale.slice(0, 2000))', source)
        self.assertIn("confirmation.checked = false", source)
        self.assertNotIn('/api/decisions', source)
        self.assertNotIn("form.submit", source)
        self.assertNotIn("requestSubmit", source)

    def test_core_recommendation_requires_all_four_positive_signals(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("criminalYes && legalYes && relationYes && sustainedYes && analyticalYes", source)
        self.assertIn('decision: "eligible_core"', source)
        self.assertIn('decision: "maybe_full_text_needed"', source)
        self.assertIn("Il codebook vieta di decidere eligibility dal titolo", source)
        self.assertIn("snapshot.evidenceMode === \"metadata\"", source)

    def test_identity_gate_blocks_recommendation_application(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn('detail?.dataset.identityBlocked === "true"', source)
        self.assertIn('detail?.dataset.scholarIdentityBlocked === "true"', source)
        self.assertIn('kind: "identity"', source)
        self.assertIn('decision: ""', source)
        self.assertIn("Prima viene l’identity gate", source)

    def test_deeper_search_is_explicit_user_action_and_bounded(self) -> None:
        source = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        self.assertIn("APPROFONDISCI", source)
        self.assertIn("async function deepenEvidence()", source)
        self.assertIn("/api/free-web-search", source)
        self.assertIn('setTimeout(() => controller.abort("assist_timeout"), 12000)', source)
        self.assertIn("Nessuna decisione viene registrata", source)

    def test_actual_abstract_and_synthesis_remain_distinguishable(self) -> None:
        assisted = (ROOT / "site/curator-assisted-resolution.js").read_text(encoding="utf-8")
        reading = (ROOT / "site/curator-reading.js").read_text(encoding="utf-8")
        self.assertIn('snapshot.evidenceMode === "abstract"', assisted)
        self.assertIn('snapshot.evidenceMode === "synthesis"', assisted)
        self.assertIn('panel.dataset.evidenceMode = "abstract"', reading)
        self.assertIn('panel.dataset.evidenceMode = "synthesis"', reading)
        self.assertIn("non è l’abstract dell’autore", reading)

    def test_component_still_loads_before_reading_surface(self) -> None:
        public = (ROOT / "site/curator-config.js").read_text(encoding="utf-8")
        worker = (ROOT / "curator-app/src/worker.js").read_text(encoding="utf-8")
        self.assertLess(public.index("curator-assisted-resolution.js"), public.index("curator-reading.js"))
        self.assertLess(
            worker.index('load(\\"./curator-assisted-resolution.js'),
            worker.index('load(\\"./curator-reading.js'),
        )
        self.assertIn('"/curator-assisted-resolution.js"', worker)

    def test_deploy_smoke_checks_component(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy-curator-worker.yml").read_text(encoding="utf-8")
        self.assertIn('"site/curator-assisted-resolution.js"', workflow)
        self.assertIn('"curator-assisted-resolution.js"', workflow)
        self.assertIn("Curator assisted abstract-resolution surface", workflow)


if __name__ == "__main__":
    unittest.main()
