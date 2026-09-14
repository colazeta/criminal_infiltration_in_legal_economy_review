"""Synthetic controls for the bounded full-text calibration source capture."""
import unittest

from scripts.calibration.full_text_source_case import candidate, PROTOCOL


CANDIDATE = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002'
URL = 'https://docs.iza.org/dp13028.pdf'


class FullTextSourceCaseTests(unittest.TestCase):
    def test_exact_existing_source_is_candidate_bound(self):
        record = candidate(CANDIDATE, URL)
        self.assertEqual(record['id'], CANDIDATE)
        self.assertEqual(record['doi'], '10.1007/s40797-020-00128-x')
        self.assertIn(URL, record['sourceLinks'])
        self.assertEqual(PROTOCOL, 'CILE-FULLTEXT-CALIBRATION-SOURCE-1')

    def test_other_or_unregistered_sources_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'url_not_candidate_bound'):
            candidate(CANDIDATE, 'https://docs.iza.org/other.pdf')
        with self.assertRaisesRegex(RuntimeError, 'candidate_not_registered'):
            candidate('CAND-NOT-REGISTERED', URL)


if __name__ == '__main__':
    unittest.main()
