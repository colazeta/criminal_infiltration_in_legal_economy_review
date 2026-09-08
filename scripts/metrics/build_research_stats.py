#!/usr/bin/env python3
"""Build public-safe daily research statistics from validated ledger records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from daily_calendar import calendar_projection, CYCLE
from scripts.surveillance_identity import is_extra
from extra_runs import project_extra_runs
from datetime import date, datetime

from surveillance import (
    REPOSITORY_FULL_NAME,
    MetricsError,
    RUN_SCHEMA_VERSION,
    build_public_payload,
    validate_public_payload,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "site/data/research-stats.json"
DEFAULT_REPOSITORY = REPOSITORY_FULL_NAME
DEFAULT_LEDGER_ISSUE = 30


def read_runs(path: Path | None) -> list[dict]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("runs"), list):
        return payload["runs"]
    raise MetricsError("Input must be a run list or an object containing runs")


def active_runs(runs):
    boundary = datetime.fromisoformat(CYCLE["reset_at"].replace("Z", "+00:00"))
    active = [r for r in runs if not is_extra(r["batch_id"]) and r["run_date"] >= CYCLE["daily_start_date"]
            and datetime.fromisoformat(r["window_start"].replace("Z", "+00:00")) >= boundary]
    if any(r.get("schema_version") != RUN_SCHEMA_VERSION for r in active):
        raise MetricsError("Active cycle requires the Exa-only v2 run contract")
    return active


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Validated ledger JSON from GitHub")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--ledger-issue", type=int, default=DEFAULT_LEDGER_ISSUE)
    parser.add_argument("--as-of", help="Explicit timezone-aware projection time; never infer successful days")
    args = parser.parse_args()
    all_runs = read_runs(args.input)
    runs = active_runs(all_runs)
    payload = build_public_payload(runs, args.ledger_issue, args.repository)
    if args.as_of:
        payload["schemaVersion"] = 2
        payload["calendar"] = calendar_projection(runs, args.as_of, date.fromisoformat(CYCLE["daily_start_date"]), CYCLE["review_id"])
    payload["extraRuns"] = project_extra_runs(all_runs, CYCLE)
    payload["schemaVersion"] = 3
    validate_public_payload(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    measured_candidates = payload["summary"]["allTime"]["newCandidates"]
    candidate_message = (
        f"{measured_candidates} intake candidate(s)."
        if measured_candidates is not None
        else "intake candidates not yet measured."
    )
    print(
        "Built daily research statistics: "
        f"{payload['summary']['runDays']} logged day(s), {candidate_message}"
    )


if __name__ == "__main__":
    try:
        main()
    except (MetricsError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
