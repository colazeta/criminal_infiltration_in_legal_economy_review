import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.curation.build_paper_support import (
    ROOT, BIBLIOGRAPHY, AID_FIELDS, ABSTRACT_FIELDS, RETRIEVAL_FIELDS, ACCESS_FIELDS,
    build_payload, safe_url, validate_payload, write_payload,
)
from scripts.curation.verify_published_register import compare_support


class PublicPaperSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.curation = self.root / 'data/curation'
        self.curation.mkdir(parents=True)
        self.bib = dict(id='CAND-TEST-001', title='A paper', authors='Author', year=2026, venue='Journal', doi='10.1/test')
        self.register = {'schemaVersion': 1, 'records': [self.bib]}
        self.aid = dict(candidateId=self.bib['id'], kind='verified_abstract_source',
            sourceLabel='Publisher', sourceUrl='https://example.org/paper',
            synopsis='A source-supported paraphrase.', checkedAt='2026-09-13',
            note='PRIVATE_SENTINEL', reviewer='PRIVATE_REVIEWER', abstract='COPY_SENTINEL')

    def aids(self, records, name='reading_aids.json'):
        (self.curation / name).write_text(json.dumps({'schemaVersion': 1, 'records': records}))

    def csv(self, name, rows):
        with (self.curation / name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def payload(self):
        return build_payload(self.root, self.register)

    def test_missing_enrichment_does_not_hide_candidate(self):
        record = self.payload()['records'][0]
        self.assertEqual(record['id'], self.bib['id'])
        self.assertIsNone(record['readingAid'])
        self.assertIsNone(record['abstract'])
        self.assertIsNone(record['retrieval'])
        self.assertIsNone(record['access'])

    def test_override_wins_without_copying_private_or_original_text(self):
        self.aids([self.aid])
        override = dict(self.aid, synopsis='Updated source-supported paraphrase.')
        self.aids([override], 'reading_aid_overrides.json')
        payload = self.payload()
        self.assertEqual(payload['records'][0]['readingAid']['synopsis'], override['synopsis'])
        encoded = json.dumps(payload)
        for sentinel in ('PRIVATE_SENTINEL', 'PRIVATE_REVIEWER', 'COPY_SENTINEL'):
            self.assertNotIn(sentinel, encoded)
        self.assertEqual(set(payload['records'][0]['readingAid']), AID_FIELDS)

    def test_unregistered_support_does_not_create_candidate(self):
        self.aids([dict(self.aid, candidateId='CAND-OTHER')])
        self.assertEqual(len(self.payload()['records']), 1)
        self.assertIsNone(self.payload()['records'][0]['readingAid'])

    def test_duplicate_source_identity_is_rejected(self):
        self.aids([self.aid, self.aid])
        with self.assertRaises(ValueError):
            self.payload()

    def test_unsafe_urls_are_not_promoted(self):
        for url in ('http://example.org', 'javascript:alert(1)', 'https://u:p@example.org', 'https://example.org/\nprivate'):
            self.assertEqual(safe_url(url), '')
        self.assertEqual(safe_url('https://example.org/paper'), 'https://example.org/paper')

    def test_coverage_and_resolver_metadata_remain_separate(self):
        cid = self.bib['id']
        self.csv('abstract_coverage.csv', [dict(candidate_id=cid, coverage_status='available', abstract_source='Provider', article_url='https://example.org/paper', checked_at='2026-09-13', notes='PRIVATE_SENTINEL')])
        self.csv('retrieval_coverage.csv', [dict(candidate_id=cid, resolution_status='full_text', full_text_url='https://example.org/paper.pdf', resolved_doi='10.1/alternate', match_confidence='medium', checked_at='2026-09-13', notes='PRIVATE_SENTINEL')])
        self.csv('access_coverage.csv', [dict(candidate_id=cid, access_status='unknown', access_kind='conflicting_full_text_evidence', access_url='https://example.org/paper.pdf', evidence_source='Assessment', checked_at='2026-09-13', notes='PRIVATE_SENTINEL', evidence_detail='PRIVATE_QUOTATION')])
        record = self.payload()['records'][0]
        self.assertEqual(record['abstract']['status'], 'available')
        self.assertEqual(record['retrieval']['resolvedDoi'], '10.1/alternate')
        self.assertEqual(record['bibliography']['doi'], '10.1/test')
        self.assertEqual(record['access']['status'], 'unknown')
        self.assertNotIn('PRIVATE_', json.dumps(record))

    def test_same_count_stale_synopsis_fails_served_comparison(self):
        self.aids([self.aid])
        expected = self.payload()
        stale = copy.deepcopy(expected)
        stale['records'][0]['readingAid']['synopsis'] = 'Old text'
        with self.assertRaisesRegex(ValueError, 'changed'):
            compare_support(expected, stale)
        self.assertEqual(compare_support(expected, expected)['changed_records'], 0)

    def test_same_count_different_identity_fails_served_comparison(self):
        expected = self.payload()
        stale = copy.deepcopy(expected)
        stale['records'][0]['id'] = 'CAND-OTHER'
        with self.assertRaisesRegex(ValueError, 'missing'):
            compare_support(expected, stale)

    def test_public_nested_field_allowlist_is_closed(self):
        self.aids([self.aid])
        payload = self.payload()
        payload['records'][0]['readingAid']['note'] = 'PRIVATE'
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_artifact_rebuild_is_deterministic(self):
        self.aids([self.aid])
        write_payload(self.root, self.register)
        path = self.root / 'site/paper-support.json'
        first = path.read_bytes()
        write_payload(self.root, self.register)
        self.assertEqual(first, path.read_bytes())
        self.assertEqual(json.loads(first), self.payload())

    def test_real_repository_support_matches_register_and_override(self):
        from scripts.curation.build_paper_register import build_payload as build_register
        register = build_register(ROOT)
        payload = build_payload(ROOT, register)
        self.assertEqual([r['id'] for r in payload['records']], [r['id'] for r in register['records']])
        self.assertEqual(payload, build_payload(ROOT, register))
        overrides = json.loads((ROOT / 'data/curation/reading_aid_overrides.json').read_text())['records']
        public = {r['id']: r for r in payload['records']}
        for aid in overrides:
            if aid['candidateId'] in public:
                self.assertEqual(public[aid['candidateId']]['readingAid']['synopsis'], aid['synopsis'].strip())

    def test_every_public_field_has_semantic_mapping(self):
        mapping = json.loads((ROOT / 'ontology/modules/public-paper-support.json').read_text())['public_fields']
        expected = {'id'} | {'bibliography.' + k for k in BIBLIOGRAPHY}
        for prefix, keys in (('readingAid', AID_FIELDS), ('abstract', ABSTRACT_FIELDS), ('retrieval', RETRIEVAL_FIELDS), ('access', ACCESS_FIELDS)):
            expected |= {prefix + '.' + k for k in keys}
        self.assertEqual(set(mapping), expected)
        profile = json.loads((ROOT / 'ontology/cile-review-profile.yaml').read_text())
        for value in mapping.values():
            self.assertTrue(value in profile['slots'] or value.split(':')[0] in profile['prefixes'], value)


if __name__ == '__main__':
    unittest.main()
