import copy
import unittest
from scripts.architecture.check_annotation_projection import check, compatibility
from scripts.enrichment.public_research_check import digest


class AnnotationProjectionCheckTest(unittest.TestCase):
    def fixture(self):
        sheets, records, index = {}, [], []
        for i in range(294):
            candidate = 'CAND-CHECK-' + str(i)
            body = dict(schema_version=1, projection_version='CILE-PUBLIC-ANNOTATIONS-1',
                        candidate_id=candidate, annotations=[], conflicts=0)
            body['revision'] = digest(body)
            sheets[candidate] = body
            classification = dict(primary=[], secondary=[], alternative=[], has_conflict=False)
            records.append(dict(candidate_id=candidate, revision=body['revision'], annotations=0,
                                conflicts=0, classification=classification))
            index.append(dict(candidate=dict(id=candidate), annotation_summary=dict(count=0,
                         conflicts=0, revision=body['revision']), classification=classification))
        audit = dict(contract='CILE-ANNOTATION-PROJECTION-AUDIT-1', commit='a' * 40,
                     index_revision='b' * 64, records=records, private_content_exported=False)
        calls = []
        def read(parameters):
            calls.append(parameters)
            if parameters['view'] == 'annotations':
                return sheets[parameters['id']]
            cursor = parameters['cursor']
            return dict(projection_version='CILE-PUBLIC-INDEX-2', index_revision=audit['index_revision'],
                        total=294, records=index[cursor:cursor+50], next_cursor=cursor+50 if cursor+50<294 else None)
        return audit, read, sheets, index, calls

    def test_every_candidate_sheet_and_index_is_checked(self):
        audit, read, _, _, calls = self.fixture()
        out = check('a' * 40, caller=lambda *a, **k: audit, reader=read)
        self.assertEqual(out['candidates_checked'], 294)
        self.assertEqual(len(calls), 300)
        self.assertTrue(out['all_current_candidates_verified'])
        self.assertFalse(out['scientific_approval_performed'])

    def test_same_count_changed_sheet_and_disagreeing_class_counts_fail(self):
        audit, read, sheets, index, _ = self.fixture()
        sheets['CAND-CHECK-293']['conflicts'] = 1
        with self.assertRaisesRegex(RuntimeError, 'annotation_sheet_mismatch'):
            check('a'*40, caller=lambda *a, **k: audit, reader=read)
        audit, read, _, index, _ = self.fixture()
        index[292]['classification'] = dict(primary=['therapy'], secondary=[], alternative=[], has_conflict=False)
        with self.assertRaisesRegex(RuntimeError, 'annotation_index_content_mismatch'):
            check('a'*40, caller=lambda *a, **k: audit, reader=read)

    def test_changed_archive_after_http_reads_is_not_certified(self):
        audit, read, *_ = self.fixture()
        changed = copy.deepcopy(audit)
        changed['index_revision'] = 'c'*64
        responses = iter([audit, changed])
        with self.assertRaisesRegex(RuntimeError, 'annotation_projection_changed'):
            check('a'*40, caller=lambda *a, **k: next(responses), reader=read)

    def test_old_backend_blocks_pages_release(self):
        with self.assertRaisesRegex(RuntimeError, 'annotation_contract_not_deployed'):
            compatibility(lambda _: dict(projection_version='CILE-PUBLIC-INDEX-1', records=[]))
