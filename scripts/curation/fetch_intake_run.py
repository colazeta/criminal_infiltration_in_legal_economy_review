#!/usr/bin/env python3
"""Wait briefly for the authenticated terminal belonging to one intake issue.

Only terminal absence is retried. Authentication, malformed target evidence,
duplicate target terminals and repository ancestry errors stop immediately.
Unrelated ledger defects cannot poison an otherwise valid target intake.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/metrics"))
from fetch_surveillance_ledger_quarantine import (  # noqa: E402
    fetch_validated_run_for_intake,
    verify_intake_issue,
    api_get,
)


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    issue = event["issue"]
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]
    if issue["user"]["login"] != owner:
        raise ValueError("intake author is not authorised")
    cycle = json.loads((ROOT / "config/archive-cycle.json").read_text())
    for attempt in range(8):
        run = fetch_validated_run_for_intake(
            os.environ["GITHUB_REPOSITORY"],
            30,
            [owner],
            os.environ["GH_TOKEN"],
            cycle,
            issue,
        )
        if run is not None:
            # Require the exact authenticated event body. An edited issue must not
            # substitute a body different from the one that triggered this run.
            live, _ = api_get(
                f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/issues/{issue['number']}",
                os.environ["GH_TOKEN"],
            )
            if any(live.get(key) != issue.get(key) for key in ("body", "title", "created_at")):
                raise ValueError("live intake differs from authenticated event; reopen the current issue")
            verify_intake_issue(run, live, {owner}, 30)
            verify_intake_issue(run, issue, {owner}, 30)
            Path(os.environ["RUNNER_TEMP"], "intake-run.json").write_text(
                json.dumps(run), encoding="utf-8"
            )
            return
        if attempt < 7:
            time.sleep(15)
    raise ValueError("terminal ledger absent; queue unchanged, reopen issue after repairing ledger")


if __name__ == "__main__":
    main()
