import copy
import json
import unittest
from datetime import datetime,timezone
from scripts.query_checkpoint import validate,render_parts,collect,identity

class QueryCheckpointTests(unittest.TestCase):
    def fixture(self):
        return {'protocol':'CILE-QUERY-CHECKPOINT-1','cycle_id':'synthetic-cycle','batch_id':'ACADEMIC-2026-09-14','provider':'Exa','query_id':'EXA-W1-Q1','attempt':1,'query':'Synthetic scholarly query','observed_at':datetime.now(timezone.utc).isoformat(),'query_status':'completed','occurrences':[{'rank':1,'url':'https://example.org/paper','title':'Synthetic title','doi':None,'year':2020}],'limitation':''}
    def comments(self,data):return [{'user':{'login':'colazeta'},'body':body} for body in render_parts(data)]
    def test_exact_observations_roundtrip_without_candidate_or_terminal(self):
        data=self.fixture();out=collect(self.comments(data));self.assertEqual(out['complete_checkpoints'][identity(data)],data);self.assertNotIn('eligible',json.dumps(out));self.assertNotIn('intake',out)
    def test_large_enumerable_query_is_multipart_and_missing_part_stays_pending(self):
        data=self.fixture();data['occurrences']=[{**data['occurrences'][0],'rank':i+1,'title':'x'*1500+str(i)} for i in range(80)]
        comments=self.comments(data);self.assertGreater(len(comments),1);out=collect(comments[:-1]);self.assertEqual(out['complete_checkpoints'],{});self.assertEqual(out['incomplete_checkpoints'],[identity(data)]);self.assertEqual(collect(comments)['complete_checkpoints'][identity(data)],data)
    def test_failed_query_remains_failed_and_old_rows_are_only_recovery_evidence(self):
        data=self.fixture();data['query_status']='partial';data['limitation']='Provider interrupted after one observed result';out=collect(self.comments(data));self.assertEqual(out['complete_checkpoints'][identity(data)]['query_status'],'partial')
    def test_conflicts_extra_text_secrets_and_false_time_fail_closed(self):
        for patch in [{'abstract':'not allowed'},{'observed_at':'2099-01-01T00:00:00Z'},{'query_status':'failed'},{'query':'Bearer secretsecretsecret'}]:
            with self.assertRaises((ValueError,TypeError)):validate({**self.fixture(),**patch})
        d=self.fixture();comments=self.comments(d);changed=copy.deepcopy(d);changed['occurrences'][0]['title']='A different result'
        with self.assertRaisesRegex(ValueError,'conflict'):collect(comments+self.comments(changed))
    def test_replayed_parts_are_idempotent_and_untrusted_authors_rejected(self):
        d=self.fixture();c=self.comments(d);self.assertEqual(collect(c+c),collect(c));c[0]['user']['login']='unknown'
        with self.assertRaises(ValueError):collect(c)

    def test_percent_encoded_credential_keys_never_enter_public_checkpoint(self):
        for query in ['%74oken=opaque','X-Amz-%53ignature=opaque','%2574oken=opaque','signature=opaque','api%5fkey=opaque','x-goog-signature=opaque']:
            d=self.fixture();d['occurrences'][0]['url']='https://example.org/paper?'+query
            with self.assertRaisesRegex(ValueError,'checkpoint_private_locator'):validate(d)
        d=self.fixture();d['occurrences'][0]['url']='https://example.org/paper?paper%5fid=123';validate(d)
