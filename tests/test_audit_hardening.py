"""Adversarial reproductions from the second audit, using synthetic evidence only."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_surveillance_metrics import candidate_issue, exa_run
from test_intake_open_access import altered_issue
import test_intake_open_access as oa_tests
from scripts.curation.import_intake_issue import import_candidates, IntakeImportError, parse_intake_issue
from scripts.intake_open_access import validate_snapshot_mapping, snapshot_semantics
from scripts.validation.validate_intake_history import validate_history
from fetch_surveillance_ledger import verify_intake_issue
from surveillance import MetricsError
from daily_calendar import calendar_projection, validate_calendar, CYCLE, SCOPES

ROOT = Path(__file__).resolve().parents[1]


class AuditHardeningTests(unittest.TestCase):
    def test_unapproved_origins_cannot_attest_access(self):
        for origin in ('not-authorised.invalid', 'zenodo.org.evil.invalid', 'api.crossref.org', 'r.jina.ai', 'zenodo.org:444'):
            def change(c):
                url = f'https://{origin}/synthetic'
                c['source_links'] = [url]
                c['open_access'].update(full_text_url=url, rights_evidence_url=url)
            issue = altered_issue(change)
            with self.assertRaises(IntakeImportError): parse_intake_issue(issue['body'], issue['title'])
            with self.assertRaises(MetricsError): verify_intake_issue(exa_run(), issue, {'colazeta'}, 30)

    def test_verification_after_issue_creation_rejected_in_both_execution_paths(self):
        for timestamp in ('2026-09-09T05:10:00Z', '2026-09-09T20:00:00Z'):
            issue = altered_issue(lambda c: c['open_access'].update(verified_at=timestamp))
            with tempfile.TemporaryDirectory() as d:
                root=Path(d); queue=oa_tests.IntakeOpenAccessTests().empty_root(root); before=queue.read_bytes()
                with self.assertRaises(IntakeImportError):
                    import_candidates(root, issue['body'], issue['title'], '201', '2026-09-09', issue_created_at=issue['created_at'])
                self.assertEqual(queue.read_bytes(), before)
            with self.assertRaises(MetricsError): verify_intake_issue(exa_run(), issue, {'colazeta'}, 30)

    def test_cycle_and_authenticated_ledger_are_required_before_production_import(self):
        for day, created, run in (
            ('2026-09-08', '2026-09-08T05:00:00Z', exa_run('2026-09-08')),
            ('2026-09-09', None, exa_run()),
            ('2026-09-09', '2026-09-09T05:00:00Z', None),
            ('2026-09-09', '2026-09-08T05:00:00Z', exa_run()),
        ):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d); queue=oa_tests.IntakeOpenAccessTests().empty_root(root)
                (root/'config').mkdir(); (root/'config/archive-cycle.json').write_text(json.dumps(CYCLE))
                issue=candidate_issue(exa_run(day),number=201)
                with self.assertRaises(IntakeImportError):
                    import_candidates(root, issue['body'],issue['title'],'201','2026-09-09',issue_created_at=created,run=run)
                self.assertFalse((root/'data/curation/intake_access').exists())

    def test_valid_production_context_imports_without_scientific_decisions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); oa_tests.IntakeOpenAccessTests().empty_root(root)
            (root/'config').mkdir(); (root/'config/archive-cycle.json').write_text(json.dumps(CYCLE))
            run=exa_run();run['intake_issue']['number']=201
            issue=candidate_issue(run,number=201)
            result=import_candidates(root,issue['body'],issue['title'],'201','2026-09-09',issue_created_at=issue['created_at'],run=run)
            self.assertEqual(len(result['added']),3)

    def test_identical_orphan_receipt_can_resume_but_changed_one_cannot(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); queue=oa_tests.IntakeOpenAccessTests().empty_root(root); before=queue.read_bytes()
            issue=candidate_issue(exa_run(),number=201)
            import_candidates(root,issue['body'],issue['title'],'201','2026-09-09')
            receipt=root/'data/curation/intake_access/ACADEMIC-2026-09-09.json'; original=receipt.read_bytes()
            queue.write_bytes(before)  # Reproduce kill after receipt publish, before queue replace.
            import_candidates(root,issue['body'],issue['title'],'201','2026-09-09')
            self.assertEqual(receipt.read_bytes(),original)
            queue.write_bytes(before);receipt.write_bytes(original+b' ')
            with self.assertRaises(FileExistsError): import_candidates(root,issue['body'],issue['title'],'201','2026-09-09')
            self.assertEqual(queue.read_bytes(),before)

    def test_committed_evidence_mutation_and_deletion_fail_against_git_base(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            def git(*args): return subprocess.check_output(['git','-C',d,*args],stderr=subprocess.DEVNULL)
            git('init');git('config','user.name','Synthetic');git('config','user.email','synthetic@example.invalid')
            path=root/'data/curation/intake_access/ACADEMIC-2026-09-09.json';path.parent.mkdir(parents=True)
            path.write_text('{"synthetic":"original"}\n');git('add','.');git('commit','-m','synthetic baseline')
            base=git('rev-parse','HEAD').decode().strip();validate_history(root,base)
            path.write_text('{"synthetic":"changed"}\n')
            with self.assertRaises(ValueError): validate_history(root,base)
            path.unlink()
            with self.assertRaises(ValueError): validate_history(root,base)
            with self.assertRaises(subprocess.CalledProcessError): validate_history(root,'f'*40)

    def test_semantic_mapping_transforms_issue_number_and_contains_receipts(self):
        module=json.loads((ROOT/'ontology/modules/intake-open-access.json').read_text())
        profile=json.loads((ROOT/'ontology/cile-review-profile.yaml').read_text())
        validate_snapshot_mapping(module,profile)
        projected=snapshot_semantics({'schema_version':1,'batch_id':'synthetic','source_issue_number':201,'source_body_sha256':'a'*64,'receipts':[{}]})
        self.assertEqual(projected['version'],'1')
        self.assertTrue(projected['was_derived_from'].endswith('/issues/201'))
        self.assertEqual(projected['contained_assessments'][0]['was_derived_from'],projected['was_derived_from'])
        broken=copy.deepcopy(module);broken['snapshot_fields']['receipts']='was_derived_from'
        with self.assertRaises(ValueError):validate_snapshot_mapping(broken,profile)
        profile['slots']['was_derived_from']['multivalued']=True
        with self.assertRaises(ValueError):validate_snapshot_mapping(module,profile)

    def test_no_ledger_cannot_claim_complete_or_hide_overdue_day(self):
        scope=CYCLE['review_id']; calendar=calendar_projection([], '2026-09-09T10:00:00Z',SCOPES[scope],scope)
        validate_calendar(calendar,[])
        for state in ('completed','planned'):
            broken=copy.deepcopy(calendar);broken['rows'][0]['status']=state
            broken.update(expectedDays=1 if state=='completed' else 0,completedDays=int(state=='completed'),missingDays=0,completionRate=1 if state=='completed' else None,sourceCompletionRate30=0 if state=='completed' else None)
            with self.assertRaises(ValueError): validate_calendar(broken,[])

class LedgerImportGateTests(unittest.TestCase):
    def test_absent_ledger_retries_then_checks_event_before_producing_context(self):
        from unittest.mock import patch
        from scripts.curation import fetch_intake_run as gate
        run=exa_run();issue=candidate_issue(run)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); event=root/'event.json';event.write_text(json.dumps({'issue':issue}))
            env={'GITHUB_EVENT_PATH':str(event),'GITHUB_REPOSITORY_OWNER':'colazeta','GITHUB_REPOSITORY':'colazeta/criminal_infiltration_in_legal_economy_review','GH_TOKEN':'synthetic','RUNNER_TEMP':d}
            with patch.dict('os.environ',env), patch.object(gate,'fetch_validated_runs',side_effect=[[],[run]]) as fetch, patch.object(gate.time,'sleep') as sleep:
                gate.main()
                self.assertEqual(fetch.call_args.args[2],['colazeta'])
                sleep.assert_called_once_with(15)
            self.assertEqual(json.loads((root/'intake-run.json').read_text())['batch_id'],run['batch_id'])

    def test_invalid_ledger_is_not_retried_and_produces_no_import_context(self):
        from unittest.mock import patch
        from scripts.curation import fetch_intake_run as gate
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);event=root/'event.json';event.write_text(json.dumps({'issue':candidate_issue(exa_run())}))
            env={'GITHUB_EVENT_PATH':str(event),'GITHUB_REPOSITORY_OWNER':'colazeta','GITHUB_REPOSITORY':'colazeta/criminal_infiltration_in_legal_economy_review','GH_TOKEN':'synthetic','RUNNER_TEMP':d}
            with patch.dict('os.environ',env), patch.object(gate,'fetch_validated_runs',side_effect=MetricsError('synthetic invalid ledger')), patch.object(gate.time,'sleep') as sleep:
                with self.assertRaises(MetricsError):gate.main()
                sleep.assert_not_called()
            self.assertFalse((root/'intake-run.json').exists())
