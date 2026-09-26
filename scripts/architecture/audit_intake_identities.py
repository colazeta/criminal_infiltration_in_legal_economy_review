"""Read-only census of every captured intake identity, including nonmaterialised IDs.

Uses the existing intake/terminal validators, captured API inputs and actual local
Git ancestry. No network, registry writes, identity decisions or recovery actions.
The private item ledger is a migration aid, not another current candidate store.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts/metrics'))
import fetch_surveillance_ledger_quarantine as governance
from scripts.curation.import_intake_issue import parse_intake_issue
from scripts.curation.stage_intake import _inventory, _validate_context
from scripts.surveillance_identity import candidate_keys

REPOSITORY = 'colazeta/criminal_infiltration_in_legal_economy_review'


def audit(capture, root=ROOT):
    root = Path(root)
    if capture.get('repository') != REPOSITORY:
        raise ValueError('capture_repository_mismatch')
    issues, comments = capture['issues'], capture['comments']
    if len({i['id'] for i in issues}) != len(issues) or len({c['id'] for c in comments}) != len(comments):
        raise ValueError('capture_duplicate_identity')
    cycle = json.loads((root / 'config/archive-cycle.json').read_text())
    with (root / 'data/curation/review_queue.csv').open(newline='', encoding='utf-8-sig') as f:
        queue = list(csv.DictReader(f))
    registered = {r['candidate_id'] for r in queue}
    if len(registered) != len(queue):
        raise ValueError('registry_duplicate_identity')
    keys, _ = _inventory(root, queue)
    main = subprocess.check_output(['git', 'rev-parse', 'origin/main'], cwd=root, text=True).strip()
    comparisons = {}
    prefix = 'https://api.github.com/repos/' + REPOSITORY

    def captured_api(url, token):
        if url == prefix + '/issues/30/comments?per_page=100':
            return [c for c in comments if c['issue_url'] == prefix + '/issues/30'], None
        if url == prefix + '/issues?state=all&per_page=100':
            return issues, None
        match = re.fullmatch(re.escape(prefix) + r'/compare/([a-f0-9]{40})\.\.\.main', url)
        if not match:
            raise ValueError('unexpected_external_read')
        sha = match[1]
        if sha not in comparisons:
            check = subprocess.run(['git', 'merge-base', '--is-ancestor', sha, main], cwd=root,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            comparisons[sha] = {'status': 'identical' if sha == main else 'ahead' if check.returncode == 0 else 'diverged',
                                'base_commit': {'sha': sha}, 'merge_base_commit': {'sha': sha if check.returncode == 0 else None}}
        return comparisons[sha], None

    candidates, batches, source_ids = [], [], set()
    today = capture['captured_at'][:10]
    with patch.object(governance, '_RAW_API_GET', captured_api):
        for issue in sorted(issues, key=lambda i: i['number']):
            if issue.get('pull_request') or not (issue.get('title') or '').startswith('[INTAKE][ACADEMIC] '):
                continue
            entry = {'source_issue_id': issue['id'], 'source_issue_number': issue['number'],
                     'source_updated_at': issue['updated_at'], 'source_sha256': hashlib.sha256(
                         json.dumps(issue, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
            try:
                manifest = parse_intake_issue(issue.get('body') or '', issue['title'])
            except Exception:
                batches.append({**entry, 'input_state': 'unparsed_input_retained'})
                continue
            entry['batch_id'] = manifest['batch_id']
            state = 'legacy_input'
            if issue['number'] > cycle['legacy_issue_ceiling']:
                try:
                    run = governance.fetch_validated_run_for_intake(REPOSITORY, 30, {'colazeta'}, '', cycle, issue)
                    state = 'terminal_absent'
                    if run is not None:
                        _validate_context(root, issue['body'], issue['title'], str(issue['number']), today, issue['created_at'], run)
                        state = 'governed_input'
                except Exception:
                    state = 'terminal_or_context_invalid'
            batches.append({**entry, 'input_state': state, 'candidate_count': len(manifest['candidates'])})
            for candidate in manifest['candidates']:
                cid = candidate['candidate_id']
                if state != 'legacy_input':
                    source_ids.add(cid)
                if cid in registered:
                    representation, matches = 'registered_candidate_id', ['candidate:' + cid]
                else:
                    matches = sorted({target for key in candidate_keys(candidate) for target in keys.get(key, set())})
                    representation = 'unregistered_possible_operational_match' if matches else 'unregistered_no_current_match'
                candidates.append({'source_issue_id': issue['id'], 'source_issue_number': issue['number'],
                                   'source_candidate_id': cid, 'input_state': state, 'representation': representation,
                                   'possible_existing_ids': matches, 'canonical_identity_established': False})
    absent = source_ids - registered
    missing_rows = [c for c in candidates if c['source_candidate_id'] in absent]
    report = {'contract': 'CILE-INTAKE-IDENTITY-CENSUS-1', 'scope': 'captured_inputs_local_git_ancestry',
              'source_captured_at': capture['captured_at'], 'ancestry_main_commit': main,
              'intake_issues': len(batches), 'batch_states': dict(collections.Counter(b['input_state'] for b in batches)),
              'registered_candidates': len(registered), 'source_candidate_ids': len(source_ids),
              'registered_ids_with_parseable_intake': len(registered & source_ids),
              'registered_ids_without_parseable_intake': len(registered - source_ids),
              'unregistered_source_ids': len(absent), 'unregistered_occurrences': len(missing_rows),
              'unregistered_occurrence_states': dict(collections.Counter(c['input_state'] for c in missing_rows)),
              'unregistered_representation': dict(collections.Counter(c['representation'] for c in missing_rows)),
              'candidate_rows_written': 0, 'canonical_identity_decisions_written': 0,
              'live_terminal_validation': False, 'authority_cutover_ready': False}
    ledger = {'contract': report['contract'], 'scope': report['scope'], 'batches': batches, 'candidate_occurrences': candidates}
    return report, ledger


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('usage')
        raw = Path(sys.argv[1]).read_bytes()
        report, ledger = audit(json.loads(raw))
        report['source_sha256'] = ledger['source_sha256'] = hashlib.sha256(raw).hexdigest()
        with open(sys.argv[2], 'x', encoding='utf-8') as output:
            import os
            os.chmod(sys.argv[2], 0o600)
            json.dump(ledger, output, ensure_ascii=False)
        print(json.dumps(report, indent=2))
    except Exception:
        raise SystemExit('intake_identity_census_failed') from None
