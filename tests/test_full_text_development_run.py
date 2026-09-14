"""Runtime-budget tests only; no model, source or network access."""
import unittest

from scripts.calibration import full_text_development as development
from scripts.calibration.full_text_development_run import (
    SCIENTIFIC_CONFIG,
    bounded_chunk_request,
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
        self.assertEqual(SCIENTIFIC_CONFIG['chunk_max_tokens'], 1000)
        fingerprint = runtime_extractor_fingerprint()
        self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')
        self.assertEqual(fingerprint, runtime_extractor_fingerprint())

    def test_chunk_request_reduces_per_call_output_budget_without_altering_source(self):
        chunk = {'id': 'chunk-1', 'text': 'Synthetic source evidence ' * 60}
        request = bounded_chunk_request(chunk)
        self.assertEqual(request['max_tokens'], 1000)
        supplied = request['messages'][1]['content']
        self.assertIn('Synthetic source evidence', supplied)
        self.assertEqual(request['temperature'], 0)
        self.assertEqual(request['seed'], 0)

    def test_base_module_is_not_mutated_merely_by_importing_runtime_policy(self):
        self.assertEqual(development.CHUNK_CHARS, 18000)
        self.assertEqual(development.CHUNK_OVERLAP, 800)
        self.assertEqual(development.MAX_ATOMS_PER_CHUNK, 18)


if __name__ == '__main__':
    unittest.main()
