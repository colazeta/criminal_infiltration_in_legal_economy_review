"""Runtime-budget tests only; no model, source or network access."""
import unittest

from scripts.calibration import full_text_development as development
from scripts.calibration.full_text_development_run import (
    EVIDENCE_UNIQUENESS_SUFFIX,
    SCIENTIFIC_CONFIG,
    bounded_chunk_request,
    runtime_chunk_system,
    runtime_extractor_fingerprint,
    runtime_post,
    runtime_timeout,
)


class FullTextDevelopmentRuntimeTests(unittest.TestCase):
    def test_operational_timeout_extension_is_bounded_and_monotone(self):
        self.assertEqual(runtime_timeout(300), 600)
        self.assertEqual(runtime_timeout(420), 720)
        self.assertEqual(runtime_timeout(900), 900)
        with self.assertRaisesRegex(ValueError, 'runtime_timeout_invalid'):
            runtime_timeout(0)

    def test_timeout_is_classified_without_changing_payload(self):
        payload = {'unchanged': True}
        seen = {}

        def timed_out(value, timeout):
            seen['payload'] = value
            seen['timeout'] = timeout
            raise TimeoutError()

        with self.assertRaisesRegex(RuntimeError, 'fulltext_model_timeout'):
            runtime_post(timed_out, payload, 300)
        self.assertIs(seen['payload'], payload)
        self.assertEqual(seen['timeout'], 600)

    def test_bounded_scientific_runtime_has_stable_explicit_fingerprint(self):
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_chars'], 6000)
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_overlap'], 400)
        self.assertEqual(SCIENTIFIC_CONFIG['max_atoms_per_chunk'], 8)
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_max_tokens'], 1600)
        fingerprint = runtime_extractor_fingerprint()
        self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')
        self.assertEqual(fingerprint, runtime_extractor_fingerprint())
        self.assertNotEqual(fingerprint, development.extractor_fingerprint())

    def test_chunk_request_expands_output_budget_and_requires_unique_literal_evidence(self):
        chunk = {'id': 'chunk-1', 'text': 'Synthetic source evidence ' * 60}
        request = bounded_chunk_request(chunk)
        self.assertEqual(request['max_tokens'], 1600)
        supplied = request['messages'][1]['content']
        self.assertIn('Synthetic source evidence', supplied)
        system = request['messages'][0]['content']
        self.assertIn(EVIDENCE_UNIQUENESS_SUFFIX, system)
        self.assertIn('occurs exactly once', system)
        self.assertIn('extend it with exact contiguous surrounding source words', system)
        self.assertIn('omit the atom', system)
        self.assertEqual(system, runtime_chunk_system() + system[len(runtime_chunk_system()):])
        self.assertEqual(request['temperature'], 0)
        self.assertEqual(request['seed'], 0)
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_chars'], 6000)
        self.assertEqual(SCIENTIFIC_CONFIG['max_atoms_per_chunk'], 8)

    def test_ambiguous_repeated_evidence_is_still_rejected_by_base_validator(self):
        text = 'start ' + ('x' * 1200) + ' repeated evidence middle repeated evidence ' + ('y' * 1200)
        chunks = development.chunk_source(text)
        outputs = []
        for chunk in chunks:
            atoms = []
            if 'repeated evidence' in chunk['text']:
                atoms.append({
                    'entity_type': 'global', 'entity_key': 'paper',
                    'field': 'research_question', 'value': 'Synthetic question',
                    'evidence': 'repeated evidence',
                })
            outputs.append({'atoms': atoms})
        with self.assertRaisesRegex(ValueError, 'ambiguous_evidence'):
            development.resolve_atoms(chunks, outputs)

    def test_base_module_is_not_mutated_merely_by_importing_runtime_policy(self):
        self.assertEqual(development.CHUNK_CHARS, 18000)
        self.assertEqual(development.CHUNK_OVERLAP, 800)
        self.assertEqual(development.MAX_ATOMS_PER_CHUNK, 18)


if __name__ == '__main__':
    unittest.main()
