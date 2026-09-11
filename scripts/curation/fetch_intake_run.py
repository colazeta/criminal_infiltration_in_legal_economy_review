#!/usr/bin/env python3
"""Wait briefly for the authenticated terminal ledger before staging an intake.

Only absence is retried. Authentication, malformed evidence and duplicate batch
errors stop immediately. No retrieval, new issue, ledger or scientific write.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/metrics'))
from fetch_surveillance_ledger_quarantine import fetch_validated_runs


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    issue = event['issue']
    owner = os.environ['GITHUB_REPOSITORY_OWNER']
    if issue['user']['login'] != owner:
        raise ValueError('intake author is not authorised')
    cycle = json.loads((ROOT / 'config/archive-cycle.json').read_text())
    for attempt in range(8):
        runs = fetch_validated_runs(os.environ['GITHUB_REPOSITORY'], 30, [owner], os.environ['GH_TOKEN'], cycle)
        matches = [r for r in runs if r['intake_issue']['number'] == issue['number']]
        if len(matches) == 1 and matches[0]['status'] == 'completed':
            # Fetcher validates live body. Require the exact authenticated event
            # body too: an edited issue must not substitute an unvalidated body.
            # Direct live-issue verification stays on the canonical module; only
            # enumeration of ledger comments uses the quarantine wrapper.
            from fetch_surveillance_ledger import verify_intake_issue, api_get
            live, _ = api_get(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{issue['number']}", os.environ['GH_TOKEN'])
            if any(live.get(key) != issue.get(key) for key in ("body", "title", "created_at")):
                raise ValueError('live intake differs from authenticated event; reopen the current issue')
            verify_intake_issue(matches[0], live, {owner}, 30)
            verify_intake_issue(matches[0], issue, {owner}, 30)
            Path(os.environ['RUNNER_TEMP'], 'intake-run.json').write_text(json.dumps(matches[0]))
            return
        if matches:
            raise ValueError('intake ledger state is not uniquely completed')
        if attempt < 7:
            time.sleep(15)
    raise ValueError('terminal ledger absent; queue unchanged, reopen issue after repairing ledger')


if __name__ == '__main__':
    main()
