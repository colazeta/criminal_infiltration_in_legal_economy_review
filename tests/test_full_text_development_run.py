"""Runtime-budget tests only; no model, source or network access."""
import unittest

from scripts.calibration.full_text_development_run import runtime_post, runtime_timeout


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


if __name__ == '__main__':
    unittest.main()
