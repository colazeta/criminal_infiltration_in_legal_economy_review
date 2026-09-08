"""Same-day manual recovery must preserve history, daily gaps and OA evidence."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from test_surveillance_metrics import candidate_issue, exa_run, completed_run, REPOSITORY
from test_exa_surveillance_policy import envelope
from scripts.surveillance_identity import batch_day, is_extra
from scripts.oa_acquisition import acquire_pdf, authorised_host, request
from scripts.intake_open_access import validate_snapshots, validate_intake_access
from scripts.curation.import_intake_issue import import_candidates, parse_intake_issue, IntakeImportError
from scripts.metrics.extra_runs import project_extra_runs
from scripts.metrics import monitor_surveillance_heartbeat as heartbeat
from build_research_stats import active_runs
from daily_calendar import CYCLE, calendar_projection
from fetch_surveillance_ledger import extract_run, fetch_validated_runs, verify_intake_issue
from surveillance import build_public_payload, validate_public_payload, validate_run, MetricsError

ROOT = Path(__file__).resolve().parents[1]


def extra(day='2026-09-08', suffix='012345abcdef'):
    run = exa_run(day)
    run.update(batch_id=f'ACADEMIC-{day}-EXTRA-{suffix}',
               window_start=f'{day}T18:00:00+02:00', window_end=f'{day}T18:20:00+02:00')
    return run


def extra_issue(run):
    issue = candidate_issue(run)
    issue['created_at'] = f'{run["run_date"]}T16:10:00Z'
    return issue


class ExtraordinaryRunTests(unittest.TestCase):
    def test_ledger_refresh_is_owner_scoped_and_never_executes_comment_text(self):
        workflow=(ROOT/'.github/workflows/archive.yml').read_text()
        self.assertIn('issue_comment:\n    types: [created]',workflow)
        self.assertIn('github.event.issue.number == 30',workflow)
        self.assertIn('github.event.comment.user.login == github.repository_owner',workflow)
        self.assertNotIn('${{ github.event.comment.body }}',workflow)
        self.assertIn('group: archive-pages',workflow)

    def test_same_day_scheduled_and_multiple_extras_are_independent(self):
        runs = [exa_run(), extra('2026-09-09'), extra('2026-09-09', 'abcdef012345')]
        self.assertEqual(len(active_runs(runs)), 1)
        payload = build_public_payload(active_runs(runs), 30, REPOSITORY)
        payload.update(schemaVersion=3, extraRuns=project_extra_runs(runs, CYCLE))
        validate_public_payload(payload)
        self.assertEqual(payload['summary']['runDays'], 1)
        self.assertEqual(len(payload['extraRuns']), 2)
        self.assertEqual(payload['summary']['allTime']['newCandidates'], 3)

    def test_extra_can_start_on_reset_day_but_not_before_reset(self):
        run = extra()
        self.assertEqual(extract_run(envelope(run)), validate_run(run))
        self.assertEqual(len(project_extra_runs([run], CYCLE)), 1)
        run['window_start'] = '2026-09-08T09:00:00+02:00'
        with self.assertRaises(ValueError): project_extra_runs([run], CYCLE)
        with self.assertRaises(ValueError): project_extra_runs([extra('2026-09-07')], CYCLE)

    def test_extra_does_not_fill_a_missing_scheduled_day_or_watchdog(self):
        run = extra('2026-09-09')
        payload = build_public_payload([], 30, REPOSITORY)
        payload.update(schemaVersion=3, extraRuns=project_extra_runs([run], CYCLE),
                       calendar=calendar_projection([], '2026-09-09T20:00:00+02:00', date(2026,9,9), CYCLE['review_id']))
        validate_public_payload(payload)
        self.assertEqual(payload['calendar']['missingDays'], 1)
        with patch('fetch_surveillance_ledger.fetch_validated_runs', return_value=[run]), patch.object(heartbeat, 'find_open_incident', return_value=None):
            self.assertEqual(heartbeat.reconcile(REPOSITORY,30,'synthetic',date(2026,9,9),dry_run=True),'opened:ACADEMIC-2026-09-09')

    def test_repeated_extra_id_and_private_public_fields_are_rejected(self):
        with self.assertRaises(ValueError): project_extra_runs([extra(),extra()],CYCLE)
        payload = build_public_payload([],30,REPOSITORY)
        payload.update(schemaVersion=3,extraRuns=project_extra_runs([extra()],CYCLE))
        for key,value in [('title','Private title'),('query','Private query')]:
            broken=copy.deepcopy(payload);broken['extraRuns'][0][key]=value
            with self.assertRaises(MetricsError): validate_public_payload(broken)
        with self.assertRaises(MetricsError): build_public_payload([extra()],30,REPOSITORY)

    def test_old_schema_cannot_claim_extra_and_invalid_dates_fail(self):
        run=completed_run('2026-09-08');run['batch_id']=extra()['batch_id']
        with self.assertRaises(MetricsError):validate_run(run)
        for batch in ('ACADEMIC-2026-02-30-EXTRA-012345abcdef','ACADEMIC-2026-09-08-EXTRA-../evil','ACADEMIC-2026-09-08-EXTRA-ABCDEF012345'):
            with self.assertRaises(ValueError):batch_day(batch)

    def test_import_extra_on_reset_day_preserves_receipt_and_pending_state(self):
        run=extra();issue=extra_issue(run)
        verify_intake_issue(run,issue,{'colazeta'},30)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir();(root/'config/archive-cycle.json').write_text(json.dumps(CYCLE))
            queue=root/'data/curation/review_queue.csv';queue.parent.mkdir(parents=True)
            queue.write_text((ROOT/'data/curation/review_queue.csv').read_text().splitlines()[0]+'\n')
            import_candidates(root,issue['body'],issue['title'],'201','2026-09-08',issue_created_at=issue['created_at'],run=run)
            self.assertEqual(validate_snapshots(root),3)
            original=queue.read_bytes()
            with self.assertRaises(IntakeImportError):import_candidates(root,issue['body'],issue['title'],'201','2026-09-08',issue_created_at=issue['created_at'],run=run)
            self.assertEqual(queue.read_bytes(),original)

    def test_duplicate_extra_ledger_is_rejected_before_second_inventory(self):
        run=extra();run['intake_issue']={'created':False,'number':None,'url':None}
        run['totals'].update(intake_candidates=0,not_forwarded=4)
        run['assessments']={k:0 for k in run['assessments']}
        run['sources'][0].update(candidate_hits=0,exclusive_candidates=0)
        comment={'body':envelope(run),'user':{'login':'colazeta'},'created_at':'2026-09-08T16:21:00Z','updated_at':'2026-09-08T16:21:00Z'}
        comparison={'status':'identical','base_commit':{'sha':'a'*40},'merge_base_commit':{'sha':'a'*40}}
        with patch('fetch_surveillance_ledger.api_get',side_effect=[([comment,comment],None),([],None),(comparison,None)]):
            with self.assertRaisesRegex(MetricsError,'duplicate batch'):fetch_validated_runs(REPOSITORY,30,['colazeta'],'synthetic',CYCLE)

    def test_changed_candidate_ids_do_not_admit_same_work_in_second_batch(self):
        first=extra('2026-09-09');second=extra('2026-09-09','abcdef012345')
        issue=extra_issue(first);other=extra_issue(second)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);queue=root/'data/curation/review_queue.csv';queue.parent.mkdir(parents=True)
            queue.write_text((ROOT/'data/curation/review_queue.csv').read_text().splitlines()[0]+'\n')
            import_candidates(root,issue['body'],issue['title'],'201','2026-09-09')
            before=queue.read_bytes()
            with self.assertRaisesRegex(IntakeImportError,'identity already present'):
                import_candidates(root,other['body'],other['title'],'202','2026-09-09')
            self.assertEqual(queue.read_bytes(),before)
            self.assertEqual(len(list((root/'data/curation/intake_access').glob('*.json'))),1)

    def test_alternative_canonical_doi_blocks_intake_without_writes(self):
        run=extra('2026-09-09');issue=extra_issue(run)
        issue['body']=issue['body'].replace('"doi": null', '"doi": "10.1234/alternative"', 1)
        candidate=parse_intake_issue(issue['body'],issue['title'])['candidates'][0]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);queue=root/'data/curation/review_queue.csv';queue.parent.mkdir(parents=True)
            queue.write_text((ROOT/'data/curation/review_queue.csv').read_text().splitlines()[0]+'\n')
            registry=root/'data/registry';registry.mkdir()
            (registry/'work_identifiers.csv').write_text('work_id,scheme,value\nwork-existing,doi,'+candidate['identifiers']['doi']+'\n')
            before=queue.read_bytes()
            with self.assertRaisesRegex(IntakeImportError,'Duplicate DOI'):
                import_candidates(root,issue['body'],issue['title'],'201','2026-09-09')
            self.assertEqual(queue.read_bytes(),before)
            self.assertFalse(list((root/'data/curation/intake_access').glob('*.json')))

    def test_canonical_stable_ids_and_citations_block_without_writes(self):
        for scheme, value, incoming in [('arxiv','2401.12345','2401.12345'),
                ('arxiv','2401.12345','arxiv:2401.12345'), ('isbn','9780123456789','9780123456789'),
                ('citation','','')]:
            with self.subTest(scheme=scheme,incoming=incoming), tempfile.TemporaryDirectory() as folder:
                run=extra('2026-09-09');issue=extra_issue(run)
                if incoming: issue['body']=issue['body'].replace('EX-1',incoming)
                candidate=parse_intake_issue(issue['body'],issue['title'])['candidates'][0]
                root=Path(folder);queue=root/'data/curation/review_queue.csv';queue.parent.mkdir(parents=True)
                queue.write_text((ROOT/'data/curation/review_queue.csv').read_text().splitlines()[0]+'\n')
                registry=root/'data/registry';registry.mkdir()
                if scheme == 'citation':
                    import csv
                    with (registry/'papers.csv').open('w',newline='') as handle:
                        writer=csv.DictWriter(handle,fieldnames=['title','year','authors']);writer.writeheader()
                        writer.writerow({'title':candidate['title'],'year':candidate['year'],'authors':'; '.join(candidate['authors'])})
                else:
                    (registry/'work_identifiers.csv').write_text('paper_id,scheme,value\nexisting,'+scheme+','+value+'\n')
                before=queue.read_bytes()
                with self.assertRaisesRegex(IntakeImportError,'identity already present'):
                    import_candidates(root,issue['body'],issue['title'],'201','2026-09-09')
                self.assertEqual(queue.read_bytes(),before)
                self.assertFalse(list((root/'data/curation/intake_access').glob('*.json')))

    def test_partial_extra_never_displays_zero_candidates(self):
        run=extra();run['status']='partial'
        source=run['sources'][0];source.update(status='failed',queries_completed=3,failure_code='connector_unavailable')
        for key in ('occurrences_returned','unique_results','candidate_hits','exclusive_candidates'):source[key]=None
        run['totals']={key:None for key in run['totals']}
        run['assessments']={key:0 for key in run['assessments']}
        run['intake_issue']={'created':False,'number':None,'url':None}
        rows=project_extra_runs([run],CYCLE)
        self.assertEqual(rows[0]['queriesCompleted'],3)
        self.assertIsNone(rows[0]['intakeCandidates'])


class OAAcquisitionTests(unittest.TestCase):
    def test_primary_publishers_and_repositories_have_explicit_host_types(self):
        self.assertEqual(authorised_host('https://www.bancaditalia.it/paper.pdf'),'publisher')
        self.assertEqual(authorised_host('https://eprints.lse.ac.uk/123/paper.pdf'),'repository')
        run=extra();candidate=parse_intake_issue(extra_issue(run)['body'],extra_issue(run)['title'])['candidates'][0]
        receipt=candidate['open_access'];receipt.update(full_text_url='https://www.bancaditalia.it/paper.pdf',rights_evidence_url='https://www.bancaditalia.it/rights',host_type='publisher')
        candidate['source_links']=[receipt['full_text_url']]
        validate_intake_access(receipt,candidate,date(2026,9,8))
        receipt['host_type']='repository'
        with self.assertRaises(ValueError):validate_intake_access(receipt,candidate,date(2026,9,8))

    def test_unknown_credentials_ports_and_lookalikes_are_not_authorised(self):
        for url in ('http://zenodo.org/a','https://zenodo.org.evil.test/a','https://user:pass@zenodo.org/a','https://zenodo.org:444/a','https://127.0.0.1/a','https://api.crossref.org/a','https://zenodo.org/a#fragment'):
            with self.assertRaises(ValueError):authorised_host(url)

    def test_redirect_cannot_escape_authorisation(self):
        transport=Mock(return_value=(302,{'location':'https://not-approved.test/paper.pdf'},b''))
        with self.assertRaises(ValueError):acquire_pdf('https://zenodo.org/paper',transport=transport)
        self.assertEqual(transport.call_count,1)

    def test_actual_pdf_bytes_are_hashed_and_final_origin_is_recorded(self):
        content=b'%PDF-1.7\nSynthetic test only\n%%EOF\n'
        transport=Mock(side_effect=[(302,{'location':'https://eprints.lse.ac.uk/paper.pdf'},b''),(200,{},content)])
        data,receipt=acquire_pdf('https://zenodo.org/paper',transport=transport)
        self.assertEqual(data,content);self.assertEqual(receipt['full_text_sha256'],hashlib.sha256(content).hexdigest())
        self.assertEqual(receipt['full_text_url'],'https://eprints.lse.ac.uk/paper.pdf')

    def test_refusals_challenges_and_incomplete_pdf_cannot_be_receipts(self):
        for status,body in ((403,b'challenge'),(429,b'rate limited'),(200,b'<html>login</html>'),(200,b'%PDF-1.7\ntruncated')):
            transport=Mock(return_value=(status,{},body))
            with self.assertRaises(ValueError):acquire_pdf('https://zenodo.org/paper.pdf',transport=transport)
            self.assertEqual(transport.call_count,1)

    def test_private_dns_is_rejected_before_connection(self):
        with patch('scripts.oa_acquisition.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),patch('scripts.oa_acquisition.socket.create_connection') as connect:
            with self.assertRaises(ValueError):request('https://zenodo.org/paper.pdf')
            connect.assert_not_called()
