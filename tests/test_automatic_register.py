import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from test_extraordinary_runs import extra, extra_issue, ROOT, CYCLE
from scripts.curation.import_intake_issue import import_candidates, parse_intake_issue, IntakeImportError
from scripts.intake_open_access import validate_snapshots
from scripts.metrics.fetch_surveillance_ledger import verify_intake_issue, extract_run, verify_ledger_comment_time
from scripts.metrics.surveillance import validate_run, MetricsError
from scripts.curation.build_paper_register import build_payload, render_page
from scripts.metrics.render_statistics_html import render_statistics_page
from scripts.metrics.extra_runs import project_extra_runs


def pending_issue():
    run=extra();run['schema_version']=3
    issue=extra_issue(extra())
    issue['body']=issue['body'].replace('"schema_version": 2','"schema_version": 3')
    pattern=r'(### Candidate records\s*```json\s*)(.*?)(\s*```)'
    match=re.search(pattern,issue['body'],re.S)
    manifest=json.loads(match[2])
    for candidate in manifest['candidates']:
        candidate['open_access']={'candidate_id':candidate['candidate_id'],'access_status':'unknown'}
        candidate['authors']=[]
    issue['body']=issue['body'][:match.start(2)]+json.dumps(manifest)+issue['body'][match.end(2):]
    return run,issue

class AutomaticRegisterTests(unittest.TestCase):
    def test_successful_persistence_refreshes_pages_independently_of_bot_push(self):
        workflow=(ROOT/'.github/workflows/archive.yml').read_text()
        self.assertIn('workflow_run:',workflow)
        self.assertIn('workflows: ["Stage daily intake in curator queue"]',workflow)
        self.assertIn('types: [completed]',workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'",workflow)
        self.assertIn('github.event.workflow_run.head_repository.full_name == github.repository',workflow)

    def test_v3_pending_access_enters_same_queue_without_scientific_decision(self):
        run,issue=pending_issue()
        validate_run(run);verify_intake_issue(run,issue,{'colazeta'},30)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir();(root/'config/archive-cycle.json').write_text(json.dumps(CYCLE))
            queue=root/'data/curation/review_queue.csv';queue.parent.mkdir(parents=True)
            queue.write_text((ROOT/'data/curation/review_queue.csv').read_text().splitlines()[0]+'\n')
            import_candidates(root,issue['body'],issue['title'],'201','2026-09-08',issue_created_at=issue['created_at'],run=run)
            self.assertEqual(validate_snapshots(root),3)
            public=build_payload(root)
            self.assertEqual(len(public['records']),3)
            for record in public['records']:
                self.assertEqual(record['reviewStatus'],'pending')
                self.assertEqual(record['accessStatus'],'unknown')
                self.assertNotIn('intake_reason',record)
                self.assertNotIn('required_human_action',record)
                self.assertNotIn('open_access',record)
            snapshot=json.loads(next((root/'data/curation/intake_access').glob('*.json')).read_text())
            self.assertEqual(snapshot['schema_version'],2)
            self.assertTrue(all(set(r)=={'candidate_id','access_status'} for r in snapshot['receipts']))

    def test_v3_envelope_is_readable_and_static_register_escapes_metadata(self):
        run,_=pending_issue()
        body=f"Daily surveillance batch {run['batch_id']}: completed.\n\n<!-- surveillance-run:v3 -->\n```json\n{json.dumps(run)}\n```"
        self.assertEqual(extract_run(body)['schema_version'],3)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'index.html';path.write_text('<p id="register-count">Loading</p><tbody id="registered-papers"></tbody>')
            render_page(path,{'records':[{'title':'<script>alert(1)</script>','authors':'A','year':2024,'venue':'V','reviewStatus':'pending','accessStatus':'unknown','sourceLinks':['https://example.org/paper']}]})
            self.assertNotIn('<script>',path.read_text())
            self.assertIn('Accesso da verificare',path.read_text())
            self.assertIn('1 record registrati',path.read_text())

    def test_v2_cannot_gain_pending_access_by_relabelling(self):
        run,issue=pending_issue()
        issue['body']=issue['body'].replace('"schema_version": 3','"schema_version": 2')
        with self.assertRaises(IntakeImportError):parse_intake_issue(issue['body'],issue['title'])

    def test_v3_does_not_waive_source_or_window_coverage(self):
        run,_=pending_issue();run['sources'][0]['queries_planned']=6
        with self.assertRaises(MetricsError):validate_run(run)
        run,_=pending_issue();run['expected_sources']=['Consensus']
        with self.assertRaises(MetricsError):validate_run(run)

    def test_unknown_access_cannot_smuggle_verification_claim(self):
        _,issue=pending_issue()
        issue['body']=issue['body'].replace('"access_status": "unknown"','"access_status": "unknown", "full_text_sha256": "'+'a'*64+'"')
        with self.assertRaises(IntakeImportError):parse_intake_issue(issue['body'],issue['title'])

    def test_deployed_statistics_contain_extra_summary_without_json_fetch(self):
        run,_=pending_issue()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stats.html';path.write_text('<p id="latest-execution" class="status-banner">Pending</p>')
            render_statistics_page(path,{'extraRuns':project_extra_runs([run],CYCLE)})
            self.assertIn('Query: 7/7',path.read_text())
            self.assertIn('Candidati inviati alla coda: 3',path.read_text())

    def test_v2_comment_cannot_be_newly_authored_after_v3_release(self):
        run=extra()
        old={'created_at':'2026-09-08T18:33:03Z','updated_at':'2026-09-08T18:33:03Z'}
        verify_ledger_comment_time(run,old)
        fresh={'created_at':'2026-09-08T20:05:10Z','updated_at':'2026-09-08T20:05:10Z'}
        with self.assertRaisesRegex(ValueError,'new surveillance requires v3'):
            verify_ledger_comment_time(run,fresh)
        run['schema_version']=3
        verify_ledger_comment_time(run,fresh)
