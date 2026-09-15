"""Regression tests for bounded synthesis timeout recovery; no model or network access."""
import unittest

from scripts.calibration import full_text_development_run as runtime


class FullTextSynthesisTimeoutRecoveryTests(unittest.TestCase):
    def test_synthesis_post_gets_bounded_extended_completion_window(self):
        seen = {}
        payload = {'kind': 'synthesis'}

        def call(value, timeout):
            seen['value'] = value
            seen['timeout'] = timeout
            return {'ok': True}

        self.assertEqual(runtime.runtime_post(call, payload, 420), {'ok': True})
        self.assertIs(seen['value'], payload)
        self.assertEqual(seen['timeout'], runtime.SYNTHESIS_COMPLETION_TIMEOUT_SECONDS)
        self.assertEqual(seen['timeout'], 1200)

    def test_chunk_post_keeps_existing_window(self):
        seen = {}

        def call(value, timeout):
            seen['timeout'] = timeout
            return {}

        runtime.runtime_post(call, {}, 300)
        self.assertEqual(seen['timeout'], runtime.CHUNK_TIMEOUT_SECONDS)
        self.assertEqual(seen['timeout'], 600)

    def test_longer_explicit_synthesis_timeout_remains_monotone(self):
        seen = {}

        def call(value, timeout):
            seen['timeout'] = timeout
            return {}

        runtime.runtime_post(call, {}, 1300)
        self.assertEqual(seen['timeout'], 1300)


if __name__ == '__main__':
    unittest.main()
