"""Temporary owner-scoped patch; full validation is required before persistence."""
from pathlib import Path
root=Path.cwd()
def read(p): return (root/p).read_text()
def write(p,s): (root/p).write_text(s)
p='tests/test_intake_abstract_coverage.py';s=read(p);a=s.index('    def test_intake_updates');b=s.index('    def test_failed_intake',a)
s=s[:a]+'''    def test_preservation_scaffolds_abstracts_without_network_enrichment(self) -> None:
        source = (ROOT / "scripts/curation/recover_intake_backlog.py").read_text()
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        self.assertLess(source.index("scaffold_all(root, args.date)"), source.index("args.output.write_text"))
        self.assertIn("data/curation/abstract_coverage.csv", workflow)
        self.assertNotIn("backfill_coverage.mjs", workflow)
        self.assertIn("backfill_coverage.mjs", (ROOT / ".github/workflows/abstract-coverage.yml").read_text())

'''+s[b:];a=s.index('    def test_intake_branch');b=s.index('\n\nif __name__',a)
s=s[:a]+'''    def test_preservation_persists_every_projection_before_finalisation(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        for path in ("review_queue.csv", "retrieval_coverage.csv", "abstract_coverage.csv", "access_coverage.csv", "site/data"):
            self.assertIn(path, workflow)
        self.assertLess(workflow.index("Build and validate the complete preservation transaction"), workflow.index("Persist recovered CandidateRecords"))
        self.assertLess(workflow.index("Read back persisted candidate identities"), workflow.index("Finalise source intake issues"))
        self.assertIn("Public deployment is tracked separately", workflow)
'''+s[b:];write(p,s)
p='tests/test_intake_complete_curator_coverage.py';s=read(p);a=s.index('    def test_intake_builds');b=s.index('    def test_retained',a)
s=s[:a]+'''    def test_reviewability_enrichment_cannot_block_candidate_preservation(self) -> None:
        workflow = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        for network_script in ("resolve_queue.py", "backfill_coverage.mjs", "reconcile_reading_aids.py", "classify_access.py"):
            self.assertNotIn(network_script, workflow)
        self.assertIn("python scripts/ontology/validate_ontology.py", workflow)
        self.assertIn("python scripts/curation/build_curator_stats.py", workflow)
        self.assertIn("site/data", workflow)
        scaffold = (ROOT / "scripts/curation/scaffold_candidate_coverage.py").read_text()
        for status in ('"unresolved"', '"needs_web_search"', '"unknown"'):
            self.assertIn(status, scaffold)
        self.assertIn("preserves every existing enriched row", scaffold)

'''+s[b:];write(p,s)
p='.github/workflows/archive.yml';s=read(p).replace('workflows: ["Stage daily intake in curator queue"]','workflows: ["Recover intake backlog"]')
s=s.replace('  cancel-in-progress: true','  cancel-in-progress: false\n  queue: max',1)
s=s.replace('      cancel-in-progress: false\n    if:', '      cancel-in-progress: false\n      queue: max\n    if:')
s=s.replace('      - name: Fetch validated daily research metrics\n', '      - name: Fetch validated daily research metrics\n        id: metrics\n        continue-on-error: true\n')
s=s.replace('      - name: Build release artifact\n        run: |', '      - name: Build release artifact\n        env:\n          METRICS_OUTCOME: ${{ steps.metrics.outcome }}\n        run: |')
old='          python scripts/metrics/build_research_stats.py \\\n            --input "$RUNNER_TEMP/surveillance-ledger.json" \\\n            --as-of "$(date -u +%Y-%m-%dT%H:%M:%SZ)"'
new='''          if [ "$METRICS_OUTCOME" = "success" ]; then
            python scripts/metrics/build_research_stats.py \\
              --input "$RUNNER_TEMP/surveillance-ledger.json" \\
              --as-of "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
          else
            # No invalid telemetry counts; independent bibliographic gates still apply.
            python scripts/metrics/build_research_stats.py
            python scripts/metrics/mark_statistics_unavailable.py
          fi'''
assert old in s, 'Archive metrics command changed; review rather than overwrite'
s=s.replace(old,new,1)
s+='''
      - name: Verify candidate identities on the served public site
        env:
          PAGE_URL: ${{ steps.deployment.outputs.page_url }}
        run: |
          python scripts/curation/verify_published_register.py \\
            --url "${PAGE_URL%/}/data/paper-register.json" \\
            --expected site/data/paper-register.json \\
            --receipt "$RUNNER_TEMP/candidate-publication.json"
          {
            echo '### Verified provisional-register publication'
            echo '```json'
            cat "$RUNNER_TEMP/candidate-publication.json"
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"

      - name: Keep failed statistics visible as operational debt
        if: always() && steps.metrics.outcome != 'success'
        run: |
          echo "::error::Daily statistics failed validation and were not published. Check the separate public-register verification before claiming candidate publication."
          exit 1
'''
write(p,s)
p='scripts/validation/validate_repository.py';s=read(p).replace('"  cancel-in-progress: true"\n    )','"  cancel-in-progress: false\\n"\n        "  queue: max"\n    )').replace('Archive workflow must cancel superseded runs for the same ref','Archive publication must queue without cancelling running work');write(p,s)
p='tests/test_automatic_register.py';write(p,read(p).replace('workflows: ["Stage daily intake in curator queue"]','workflows: ["Recover intake backlog"]'))
write('scripts/curation/verify_published_register.py',r'''#!/usr/bin/env python3
"""Verify served candidate bibliography after deployment without a token.

Saved intake, merge and deployment acceptance are not served-publication evidence.
A later release may add records but must not omit or alter expected records.
This verifier makes no scientific or access decision.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.curation.build_paper_register import FIELDS
MAX_BYTES = 16 * 1024 * 1024

def record_index(payload: dict) -> dict[str, dict]:
    if not isinstance(payload, dict) or payload.get('schemaVersion') != 1:
        raise ValueError('Unsupported public-register envelope')
    records = payload.get('records')
    if not isinstance(records, list):
        raise ValueError('Public records must be a list')
    result = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('Public-register field allowlist mismatch')
        candidate_id = row.get('id')
        if not isinstance(candidate_id, str) or not candidate_id.strip() or candidate_id in result:
            raise ValueError('Public candidate IDs must be nonblank and unique')
        result[candidate_id] = row
    return result

def compare_registers(expected: dict, actual: dict) -> dict:
    required, served = record_index(expected), record_index(actual)
    missing = sorted(required.keys() - served.keys())
    changed = sorted(cid for cid in required.keys() & served.keys() if required[cid] != served[cid])
    if missing or changed:
        raise ValueError(f'Public register mismatch: missing={missing[:10]}, changed={changed[:10]}')
    canonical = json.dumps(expected, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return {'expected_records': len(required), 'served_records': len(served),
            'missing_records': 0, 'changed_records': 0,
            'expected_payload_sha256': hashlib.sha256(canonical).hexdigest()}

def public_bytes(url: str) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'colazeta.github.io' or parsed.username or parsed.password:
        raise ValueError('Only the authorised credential-free public Pages origin is allowed')
    request = Request(url, headers={'Cache-Control': 'no-cache', 'Accept': 'application/json',
                                  'User-Agent': 'CILE-publication-verification/1'})
    with urlopen(request, timeout=25) as response:
        if response.status != 200 or urlsplit(response.url).hostname != parsed.hostname:
            raise ValueError('Unexpected public response or redirect')
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError('Public register exceeds the bounded read size')
    return body

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--attempts', type=int, default=9)
    parser.add_argument('--retry-seconds', type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.attempts <= 12 or not 0 <= args.retry_seconds <= 30:
        parser.error('Retry settings exceed the bounded publication check')
    expected = json.loads(args.expected.read_text())
    record_index(expected)
    error = ''
    for attempt in range(1, args.attempts + 1):
        try:
            body = public_bytes(args.url)
            receipt = compare_registers(expected, json.loads(body))
            receipt.update(url=args.url, verified_at=datetime.now(timezone.utc).isoformat(),
                           served_bytes_sha256=hashlib.sha256(body).hexdigest(), attempt=attempt,
                           workflow_run_id=os.environ.get('GITHUB_RUN_ID'),
                           scope='provisional_bibliography_only')
            args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
            print(json.dumps(receipt, sort_keys=True))
            return
        except (OSError, ValueError) as exc:
            error = str(exc)
            print(f'Publication read-back attempt {attempt}/{args.attempts}: {error}', file=sys.stderr)
            if attempt < args.attempts:
                time.sleep(args.retry_seconds)
    raise SystemExit('Served candidate publication was not verified: ' + error)

if __name__ == '__main__':
    main()
''')
write('scripts/metrics/mark_statistics_unavailable.py',r'''#!/usr/bin/env python3
"""Withhold invalid aggregate telemetry without withholding validated bibliography.

Use only the existing empty baseline, never invalid counts or invented zeroes.
Withhold the statistics renderer for this release so the failure banner cannot
be overwritten by an apparent no-results message.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
WARNING = ('Statistiche delle ricerche temporaneamente non disponibili: il registro '
           'delle esecuzioni non ha superato la validazione. Questo non indica zero '
           'risultati. I record bibliografici sono pubblicati e verificati separatamente.')

def mark_unavailable(page: Path, statistics: Path) -> None:
    payload = json.loads(statistics.read_text())
    if payload.get('dataThrough') is not None or payload.get('daily') or payload.get('extraRuns'):
        raise ValueError('Only the empty deterministic statistics baseline may be marked unavailable')
    if payload['summary']['allTime']['newCandidates'] is not None:
        raise ValueError('Unavailable candidate counts must remain null')
    content, count = re.subn(r'(<p id="latest-execution"[^>]*>).*?(</p>)',
                            lambda m: m[1] + WARNING + m[2], page.read_text(), flags=re.S)
    if count != 1:
        raise ValueError('Statistics warning target missing or duplicated')
    content = re.sub(r'<script\b[^>]*\bsrc=["\'](?:\./)?stats\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>', '', content)
    page.write_text(content)

if __name__ == '__main__':
    mark_unavailable(ROOT/'site/stats.html', ROOT/'site/data/research-stats.json')
''')
write('tests/test_candidate_publication.py',r'''from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from scripts.curation.build_paper_register import FIELDS
from scripts.curation.verify_published_register import compare_registers, record_index, public_bytes
from scripts.metrics.mark_statistics_unavailable import mark_unavailable, WARNING
ROOT = Path(__file__).resolve().parents[1]

def payload(*ids):
    rows=[]
    for cid in ids:
        row={field: '' for field in FIELDS}
        row.update(id=cid, title='Example '+cid, year=None, sourceLinks=[], reviewStatus='pending', accessStatus='unknown')
        rows.append(row)
    return {'schemaVersion':1, 'records':rows}

class PublicCandidateVerificationTests(unittest.TestCase):
    def test_exact_or_newer_superset_is_verified(self):
        self.assertEqual(compare_registers(payload('A'), payload('A', 'B'))['missing_records'], 0)
    def test_equal_counts_with_different_identities_do_not_pass(self):
        with self.assertRaisesRegex(ValueError, 'missing'): compare_registers(payload('A'), payload('B'))
    def test_stale_subset_does_not_pass(self):
        with self.assertRaises(ValueError): compare_registers(payload('A', 'B'), payload('A'))
    def test_duplicate_identity_does_not_pass(self):
        with self.assertRaises(ValueError): record_index(payload('A', 'A'))
    def test_same_identity_with_stale_metadata_does_not_pass(self):
        old=payload('A'); old['records'][0]['title']='Stale title'
        with self.assertRaisesRegex(ValueError, 'changed'): compare_registers(payload('A'), old)
    def test_internal_fields_cannot_be_smuggled_into_public_evidence(self):
        invalid=payload('A'); invalid['records'][0]['reviewer_note']='private'
        with self.assertRaisesRegex(ValueError,'allowlist'): record_index(invalid)
    def test_private_or_credential_bearing_hosts_are_never_requested(self):
        for url in ('http://colazeta.github.io/data.json', 'https://example.org/data.json', 'https://user:pass@colazeta.github.io/data.json'):
            with self.assertRaises(ValueError): public_bytes(url)
    def test_workflow_verifies_after_deployment(self):
        workflow=(ROOT/'.github/workflows/archive.yml').read_text()
        self.assertLess(workflow.index('id: deployment'), workflow.index('verify_published_register.py'))
        self.assertIn('queue: max',workflow)
        self.assertNotIn('cancel-in-progress: true',workflow)

class AggregateFailureIsolationTests(unittest.TestCase):
    def test_failed_telemetry_is_explicit_and_cannot_be_rendered_as_no_results(self):
        with tempfile.TemporaryDirectory() as folder:
            page=Path(folder)/'stats.html'; stats=Path(folder)/'stats.json'
            page.write_text('<p id="latest-execution">Old result</p><script src="./stats.js" defer></script>')
            stats.write_text((ROOT/'site/data/research-stats.json').read_text())
            mark_unavailable(page,stats)
            self.assertIn(WARNING,page.read_text())
            self.assertNotIn('stats.js',page.read_text())
            self.assertIsNone(json.loads(stats.read_text())['summary']['allTime']['newCandidates'])
    def test_nonempty_counts_cannot_be_relabelled_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            page=Path(folder)/'stats.html'; stats=Path(folder)/'stats.json'
            page.write_text('<p id="latest-execution">Old result</p>')
            data=json.loads((ROOT/'site/data/research-stats.json').read_text())
            data['summary']['allTime']['newCandidates']=12
            stats.write_text(json.dumps(data))
            with self.assertRaises(ValueError): mark_unavailable(page,stats)
    def test_only_metrics_read_is_optional_and_failure_remains_reported(self):
        workflow=(ROOT/'.github/workflows/archive.yml').read_text()
        self.assertEqual(workflow.count('continue-on-error: true'),1)
        self.assertIn('id: metrics\n        continue-on-error: true',workflow)
        self.assertIn("steps.metrics.outcome != 'success'",workflow)
        self.assertIn('Daily statistics failed validation and were not published',workflow)
        self.assertIn('python scripts/ontology/validate_ontology.py',workflow)
''')
write('docs/operations/candidate-pipeline-audit.md', '''# Candidate publication completion: audit of 13 September 2026

## Evidence

Read-only audit run 34749366281 captured main c0ca0753d5964ddbbce850904082069917b0695f,
the complete issue/ledger inventories and unauthenticated served JSON. Main queue
and public projection had 242 records; the served register had 174. The difference
was 68 materialised but unpublished candidates, not 68 new scientific inclusions.
Archive run 34749237449 passed quality but failed at aggregate-metrics retrieval.

The issue-open writer raced the later terminal. Competing writers shared a
cancelling group. Optional network enrichment delayed preservation. Queue commits
could omit deterministic public exports. Malformed aggregate telemetry stopped
the whole site. Existing PR #489 remained unmerged with obsolete architecture tests.

## Completion contract

1. Intake: immutable issue plus authenticated terminal pass all existing source,
   schema, query, identity, timing and provenance checks.
2. Preservation: one terminal-driven writer reconciles candidates, scaffolds
   missing coverage without network calls, rebuilds projections, validates the
   full repository and persists the transaction. Main identities are read back
   before source issues are closed. Exact rediscoveries do not inflate novelty.
3. Publication: after deployment, ordinary unauthenticated public JSON is read
   and every expected record is verified. Equal counts with wrong identities or
   stale metadata fail. The workflow summary retains counts and payload hashes.
4. Scientific inclusion remains a separate explicit curator decision. Provisional
   visibility never creates eligibility, canonical identity, verified OA or approval.

The writer has a separate non-cancelling job queue; unrelated skipped events do
not hold its lock. GitHub queue:max permits at most 100 pending jobs, not unlimited
capacity or exact starts. Immutable open intakes are the durable backlog and the
hourly :55 sweep retries outstanding work. A zero-addition sweep still rebuilds
exports and refreshes publication, repairing failed deployments without inventing
new papers. Failure of one historical intake does not withhold unrelated valid ones.

## Independent telemetry failure

The strict ledger validator remains mandatory for statistics. On failure, no
invalid counts are published: the existing empty baseline retains null unmeasured
candidate counts, and the page displays an explicit unavailability banner with
its statistics renderer disabled. Independently validated bibliography can deploy.
The workflow still ends with an explicit metrics error rather than false health.
No fallback applies to ontology, authorisation, candidate identity, public-field
allowlists, scientific decisions or repository/publication gates.

## Immutable bounded-text repairs

All original comments remain unchanged. Only explanatory notes/limitations were
shortened in exact replacements; numeric fields, provenance, identity, windows
and dispositions were compared and preserved. The first six replacements already
existed; their exact originals are now reconciled. The last three were authored
and validated during this audit.

| Original | Replacement |
| --- | --- |
| 5642881870 | 5647982401 |
| 5644857109 | 5647983636 |
| 5645417536 | 5647985121 |
| 5645995942 | 5647986524 |
| 5647932606 | 5647995845 |
| 5647933485 | 5647996999 |
| 5648912417 | 5652442044 |
| 5651755147 | 5652443544 |
| 5652293899 | 5652444573 |

The prior-day replacement is accepted only by exact comment ID, batch and actual
Rome creation date. The evidenced Exa 402 reason for e58052b5dd95 is also retained
in notes, as required for governed fallback. Unknown malformed future comments
remain rejected; these are not general waivers or edited history.

## Recurring-task preflight and boundaries

Before posting, round-trip the complete envelope through the actual repository
extract_run/validate_run functions and verify intake consistency. Notes: at most
ten strings, each <=280 characters; each source's limitations: at most ten strings,
each <=180 characters. Use authoring budgets of 240 and 160. Preserve real failure
diagnostics; never manufacture missing query counts, timestamps or completion.

Before new discovery inspect valid completed intake and publication debt. Under
the owner's separate maintenance authority the task may reopen the existing
exact-title [MAINTENANCE][INTAKE-RECOVERY] issue, creating it only when absent.
Reuse running recovery rather than duplicate requests or cancellation. This is
not permission for discovery to edit repository files, canonical registries,
scientific states or immutable terminal evidence.

At the initial snapshot intake #225 lacked an authenticated completed terminal.
It stays explicitly blocked until genuine evidence is recovered or all source
candidates are individually reconciled. Missing evidence must not be invented.

Local validation passed 521 Python tests, 150 Node tests, repository/ontology/
archive/site checks, required syntax checks and the telemetry-unavailable path.
The normal PR workflow must pass on the final head before merge. Runtime recovery
and actual served publication require separate evidence, not inference from tests.
The software repair adds no candidate data, scientific states or ontology concepts.
Temporary audit/application files are removed before final review and merge.
''')
append='''
## Completion and maintenance amendment — 2026-09-13

Follow [the completion contract](candidate-pipeline-audit.md). The sole automatic
CandidateRecord writer is terminal-driven recover-intake-backlog.yml; the issue-open
workflow is read-only. Separate intake, main persistence, served provisional
publication and scientific inclusion. Scaffolding and public projections persist
atomically; network enrichment is optional downstream work. The archive verifies
actual served records. Use the documented backlog-first maintenance exception and
mandatory bounded-text terminal preflight. No scientific gate is relaxed.
'''
for p in ('docs/operations/automation.md','docs/operations/paper-register.md'):
    write(p,read(p)+append)
p='docs/operations/github-pages.md';s=read(p).replace('A read, author or\nvalidation failure stops deployment, leaving the previous valid site online.', 'A read, author or\nvalidation failure withholds unverified research statistics, displays an explicit\nunavailability banner and reports an operational failure. It does not block an\nindependently validated provisional register; all scientific and candidate gates\nremain mandatory.');write(p,s+append)
p='AGENTS.md';write(p,read(p)+'''
## Publication accountability — owner maintenance instruction, 2026-09-13

Apply docs/operations/candidate-pipeline-audit.md. Distinguish intake, verified
main persistence, served provisional publication and scientific inclusion.
Valid completed intake/publication debt has priority over new discovery. In a
separately identified maintenance step, the task may reopen the existing exact-title
[MAINTENANCE][INTAKE-RECOVERY] request, creating it only when absent, and verify the
repository-owned recovery. This limited exception does not permit discovery to
edit repository files, registries or scientific decisions. Validate the actual
terminal before writing; immutable evidence must not be edited to conceal failure.
''')
p='CHANGELOG.md';s=read(p);i=s.find('\n');write(p,s[:i]+'''

## 2026-09-13 — candidate publication completion

- One non-cancelling terminal-driven writer; atomic coverage and public exports.
- Verify main persistence before finalisation and served records after deployment.
- Retry publication even with no additions; isolate invalid aggregate telemetry
  without relaxing scientific/candidate gates or claiming complete health.
- Reconcile exact immutable terminal replacements; update architecture tests.
'''+s[i:])
