import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SupportQualityWaitTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("jq"), "jq is required by the Actions persistence helper")
    def test_rerun_waits_for_new_check_and_still_rejects_its_failure(self):
        script = (ROOT / "scripts/retrieval/persist_selected_support.sh").read_text()
        functions = script[script.index("quality_ignored_ids="):script.index("\nquality_state=")]
        checks = [
            {"id": 10, "status": "completed", "conclusion": "failure", "started_at": "2026-09-27T10:00:00Z"},
            {"id": 11, "status": "in_progress", "conclusion": None, "started_at": "2026-09-27T10:01:00Z"},
        ]
        shell = 'set -euo pipefail\nGITHUB_REPOSITORY=x/y\nhead_sha=abc\n'
        shell += 'gh() { printf "%s\\n" "$TEST_CHECKS"; }\n' + functions + '\n'
        shell += "TEST_CHECKS='" + json.dumps(checks[:1]) + "'\nlatest_quality_state\n"
        shell += "quality_ignored_ids='[10]'\nlatest_quality_state\n"
        shell += "TEST_CHECKS='" + json.dumps(checks) + "'\nlatest_quality_state\n"
        checks[1].update(status="completed", conclusion="failure")
        shell += "TEST_CHECKS='" + json.dumps(checks) + "'\nlatest_quality_state\n"
        checks[1]["conclusion"] = "success"
        shell += "TEST_CHECKS='" + json.dumps(checks) + "'\nlatest_quality_state\n"
        result = subprocess.run(["bash", "-c", shell], text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ["blocked", "missing", "pending", "blocked", "success"])

    def test_intake_recovery_has_one_pages_trigger(self):
        archive = (ROOT / ".github/workflows/archive.yml").read_text()
        recovery = (ROOT / ".github/workflows/recover-intake-backlog.yml").read_text()
        self.assertNotIn('workflows: ["Recover intake backlog"', archive)
        self.assertIn('gh workflow run archive.yml --ref main', recovery)
