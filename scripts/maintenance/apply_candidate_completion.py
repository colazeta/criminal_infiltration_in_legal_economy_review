"""Temporary, owner-scoped maintenance patch. Removed before final PR review."""
from pathlib import Path
import re
root=Path.cwd()
def change(path,old,new):
    p=root/path; s=p.read_text(); assert s.count(old)==1,(path,old[:80],s.count(old)); p.write_text(s.replace(old,new,1))
p=root/'.github/workflows/intake-to-curation.yml';s=p.read_text();start=s.index('# Legacy intake safeguard');end=s.index('\njobs:',start);s=s[:start]+'# Issue-open preserves the immutable source; only terminal-driven recovery writes candidates.\n'+s[end:];p.write_text(s)
p=root/'.github/workflows/recover-intake-backlog.yml';s=p.read_text();s=s.replace('concurrency:\n  group: candidate-conservation-main\n  cancel-in-progress: false\n','')
s=s.replace('    runs-on: ubuntu-latest\n','    concurrency:\n      group: candidate-conservation-main\n      cancel-in-progress: false\n      queue: max\n    runs-on: ubuntu-latest\n    timeout-minutes: 20\n',1)
s=s.replace('      - name: Reconcile every outstanding governed intake','      - name: Set up Node.js\n        uses: actions/setup-node@a0853c24544627f65ddf259abe73b1d18a591444 # v5\n        with:\n          node-version: 22\n\n      - name: Reconcile every outstanding governed intake',1)
a=s.index('      - name: Validate candidate-preservation state');b=s.index('      - name: Persist recovered CandidateRecords',a)
s=s[:a]+'''      - name: Build and validate the complete preservation transaction
        id: projection
        run: |
          python scripts/build_archive.py
          python scripts/build_secondary_collections.py
          python scripts/metrics/build_research_stats.py
          python scripts/curation/build_curator_stats.py
          python scripts/curation/build_curator_options.py
          python scripts/curation/build_legacy_queue.py --check
          python scripts/validation/validate_intake_history.py --base HEAD
          python scripts/validation/validate_repository.py
          python scripts/ontology/validate_ontology.py
          python scripts/ontology/build_model_browser.py
          git diff --exit-code -- site/vocab/review-v2-model.json
          python -m unittest discover -s tests -p 'test_*.py'
          python scripts/validation/validate_archive.py
          python scripts/validation/validate_site.py
          for script in site/*.js curator-app/src/*.js; do node --check "$script"; done
          node --test curator-app/test/*.test.js
          python scripts/report_saturation.py
          if git diff --quiet HEAD -- data/curation site/data; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi

'''+s[b:]
s=s.replace("if: steps.recovery.outputs.added_count != '0'", "if: steps.projection.outputs.changed == 'true'")
s=s.replace('git add data/curation/review_queue.csv data/curation/intake_access','git add data/curation/review_queue.csv data/curation/intake_access \\\n            data/curation/retrieval_coverage.csv data/curation/abstract_coverage.csv \\\n            data/curation/access_coverage.csv site/data')
s=s.replace("if: steps.recovery.outputs.added_count == '0'", "if: steps.projection.outputs.changed == 'false'")
a=s.index('      - name: Finalise source intake issues after persistence')
s=s[:a]+'''      - name: Read back persisted candidate identities from main
        id: readback
        if: steps.persist.outputs.persisted == 'true' || steps.nochange.outputs.persisted == 'true'
        run: |
          git fetch origin main
          git show origin/main:data/curation/review_queue.csv > "$RUNNER_TEMP/persisted-queue.csv"
          git show origin/main:site/data/paper-register.json > "$RUNNER_TEMP/persisted-register.json"
          python3 - <<'PY_READBACK'
          import csv, json, os
          from pathlib import Path
          root = Path(os.environ['RUNNER_TEMP'])
          report = json.loads((root/'intake-recovery.json').read_text())
          queue = {r['candidate_id'] for r in csv.DictReader((root/'persisted-queue.csv').open())}
          public = {r['id'] for r in json.loads((root/'persisted-register.json').read_text())['records']}
          added = {cid for row in report['processed'] for cid in row['added']}
          if queue != public or not added <= queue:
              raise SystemExit('Persisted queue/public projection mismatch; no intake may be finalised')
          print(f'Persisted identity read-back: {len(queue)} candidates; {len(added)} additions verified')
          PY_READBACK
          echo "verified=true" >> "$GITHUB_OUTPUT"
          echo "sha=$(git rev-parse origin/main)" >> "$GITHUB_OUTPUT"

'''+s[a:]
s=s.replace("          steps.persist.outputs.persisted == 'true' || steps.nochange.outputs.persisted == 'true'\n        env:","          steps.readback.outputs.verified == 'true'\n        env:",1)
s=s.replace('No scientific eligibility or canonical duplicate decision was inferred. Persistence:', 'Public deployment is tracked separately and is not yet claimed. No scientific eligibility or canonical duplicate decision was inferred. Persistence:')
s=re.sub(r'(      - name: Refresh operational archive\n)        if: .*\n',r"\1        if: steps.readback.outputs.verified == 'true'\n",s)
s=s.replace('          ADDED: ${{ steps.recovery.outputs.added_count }}','          VERIFIED: ${{ steps.readback.outputs.verified }}\n          ADDED: ${{ steps.recovery.outputs.added_count }}',1)
s=s.replace('          summary="Candidate conservation:','          materialised=0\n          if [ "$VERIFIED" = "true" ]; then materialised="${ADDED:-0}"; fi\n          summary="Candidate conservation:',1)
s=s.replace('${ADDED:-0} CandidateRecord(s) materialised','${ADDED:-0} candidate(s) staged, ${materialised} CandidateRecord(s) verified on main')
s=s.replace('if [ "${FAILURES:-0}" = "0" ] && [ -n "${PERSISTENCE:-}" ]; then','if [ "${FAILURES:-0}" = "0" ] && [ "$VERIFIED" = "true" ]; then')
s=s.replace("(steps.recovery.outputs.added_count != '0' && steps.persist.outputs.persisted != 'true'))", "(steps.recovery.outputs.added_count != '0' && steps.readback.outputs.verified != 'true'))")
p.write_text(s)
p=root/'scripts/validation/validate_repository.py';s=p.read_text();a=s.index('    intake = (\n',s.index('def check_actions_pinned'));b=s.index('\n\ndef check_release_metadata',a)
s=s[:a]+'''    intake = (ROOT / ".github/workflows/intake-to-curation.yml").read_text(encoding="utf-8")
    recovery = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text(encoding="utf-8")
    # Comments must not satisfy execution safeguards.
    intake = "\\n".join(line for line in intake.splitlines() if not line.lstrip().startswith("#"))
    recovery = "\\n".join(line for line in recovery.splitlines() if not line.lstrip().startswith("#"))
    for required in ("github.actor == github.repository_owner", "[INTAKE][ACADEMIC] ",
                     "defer-to-terminal-recovery:", "persist-credentials: false"):
        if required not in intake:
            fail(f"Intake terminal-deferral safeguard missing: {required}")
    for forbidden in ("stage_intake.py", "git push", "contents: write", "gh issue close"):
        if forbidden in intake:
            fail(f"Issue-open must not mutate candidates: {forbidden}")
    for required in ("group: candidate-conservation-main", "cancel-in-progress: false",
                     "queue: max", "recover_intake_backlog.py", "surveillance-run:v3",
                     "github.event.issue.number == 30", "build_curator_stats.py",
                     "data/curation/review_queue.csv", "site/data", "validate_repository.py",
                     "Read back persisted candidate identities from main", "gh workflow run archive.yml"):
        if required not in recovery:
            fail(f"Candidate recovery safeguard missing: {required}")
    for forbidden in ("resolve_queue.py", "backfill_coverage.mjs", "classify_access.py"):
        if forbidden in recovery:
            fail(f"Optional enrichment blocks candidate preservation: {forbidden}")
'''+s[b:];p.write_text(s)
change('tests/test_intake_backlog_recovery.py','self.assertIn("group: intake-to-curation-main", workflow)\n        self.assertIn("scripts/curation/stage_intake.py", workflow)\n        self.assertIn("Close rediscovery-only intake", workflow)\n        self.assertIn("gh issue close", workflow)', 'self.assertIn("defer-to-terminal-recovery", workflow)\n        self.assertNotIn("scripts/curation/stage_intake.py", workflow)\n        self.assertNotIn("gh issue close", workflow)\n        self.assertIn("persist-credentials: false", workflow)')
change('tests/test_intake_backlog_recovery.py','self.assertIn("group: intake-to-curation-main", workflow)','self.assertIn("group: candidate-conservation-main", workflow)\n        self.assertIn("cancel-in-progress: false", workflow)\n        self.assertIn("queue: max", workflow)')
change('tests/test_retrieval_resolution.py','self.assertIn("resolve_queue.py", intake)','self.assertNotIn("resolve_queue.py", intake)\n        self.assertIn("defer-to-terminal-recovery", intake)')
p=root/'tests/test_intake_persistence.py';s=p.read_text().replace('.github/workflows/intake-to-curation.yml','.github/workflows/recover-intake-backlog.yml');s=s.replace('$BRANCH','$branch').replace('$BASE_SHA','$base_sha').replace('"Validated intake merged automatically"','"persisted=true"').replace('"Validated intake could not be persisted automatically"','"CandidateRecords were staged but could not cross the persistence barrier"').replace('"Validated branch retained"',"'git push origin \"$branch\"'")
s=s.replace('self.assertIn("Expected main SHA", workflow)','self.assertIn(\'base_sha="$(git rev-parse HEAD)"\', workflow)').replace('self.assertIn("Current main SHA", workflow)','self.assertIn(\'current_main="$(git rev-parse origin/main)"\', workflow)');p.write_text(s)
p=root/'tests/test_candidate_conservation.py';s=p.read_text().replace("steps.persist.outputs.persisted != 'true'","steps.readback.outputs.verified != 'true'");p.write_text(s)
p=root/'scripts/metrics/fetch_surveillance_ledger_quarantine.py';s=p.read_text();marker='QUARANTINED_LEDGER_COMMENTS = {\n'; additions={5642881870:'ACADEMIC-2026-09-12-EXTRA-8943d605c4aa',5644857109:'ACADEMIC-2026-09-12-EXTRA-486aaf42fb90',5645417536:'ACADEMIC-2026-09-12-EXTRA-748af9c3f874',5645995942:'ACADEMIC-2026-09-12-EXTRA-069e6c0a5fa8',5647932606:'ACADEMIC-2026-09-12-EXTRA-4faa0ba491c4',5647933485:'ACADEMIC-2026-09-12-EXTRA-9bdb3c1e67c7',5648912417:'ACADEMIC-2026-09-12-EXTRA-2d5ea81ff42e',5651755147:'ACADEMIC-2026-09-13-EXTRA-e58052b5dd95',5652293899:'ACADEMIC-2026-09-13-EXTRA-df65ea613c7f'}
s=s.replace(marker,marker+'    # Bounded-text audit 2026-09-13: originals remain immutable.\n'+''.join(f'    {k}: "{v}",\n' for k,v in additions.items()),1)
new={5652442044:('ACADEMIC-2026-09-12-EXTRA-2d5ea81ff42e','2026-09-12'),5652443544:('ACADEMIC-2026-09-13-EXTRA-e58052b5dd95','2026-09-13'),5652444573:('ACADEMIC-2026-09-13-EXTRA-df65ea613c7f','2026-09-13')};s=s.replace('LATE_RECOVERY_TERMINALS = {\n','LATE_RECOVERY_TERMINALS = {\n'+''.join(f'    {k}: {{"batch_id": "{v[0]}", "run_date": "{v[1]}", "created_rome_date": "2026-09-13"}},\n' for k,v in new.items()),1);p.write_text(s)
