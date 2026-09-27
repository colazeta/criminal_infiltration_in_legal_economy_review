#!/usr/bin/env python3
"""Validate a prospective immutable ledger body before a GitHub write.

This read-only preflight proves neither persistence nor intake uniqueness. The
repository ledger reader still verifies remote author, ancestry and intake.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from daily_calendar import CYCLE
from fetch_surveillance_ledger import extract_run, verify_ledger_comment_time
from scripts.surveillance_identity import validate_cycle_run
from surveillance import MetricsError


def validate(body: str, expected_batch: str, now: datetime | None = None) -> dict:
    run = extract_run(body)
    if run is None:
        raise MetricsError("canonical surveillance terminal is missing")
    if run["schema_version"] != 3 or run["batch_id"] != expected_batch:
        raise MetricsError("prospective terminal version or batch differs from the intended write")
    validate_cycle_run(run, CYCLE)
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise MetricsError("preflight clock must be timezone-aware")
    stamp = instant.isoformat()
    verify_ledger_comment_time(run, {"created_at": stamp, "updated_at": stamp})
    return {"batch_id": run["batch_id"], "status": run["status"],
            "schema_valid": True, "prospective_timestamp_valid": True,
            "persisted": False, "remote_validation_required": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--expected-batch", required=True)
    args = parser.parse_args()
    try:
        result = validate(args.body.read_text(encoding="utf-8"), args.expected_batch)
    except (MetricsError, ValueError, OSError) as exc:
        raise SystemExit(f"[FAIL] terminal preflight: {exc}") from exc
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
