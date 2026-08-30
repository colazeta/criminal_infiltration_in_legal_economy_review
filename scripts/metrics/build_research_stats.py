#!/usr/bin/env python3
"""Build public-safe daily research statistics from validated ledger records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from surveillance import (
    REPOSITORY_FULL_NAME,
    MetricsError,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Validated ledger JSON from GitHub")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--ledger-issue", type=int, default=DEFAULT_LEDGER_ISSUE)
    args = parser.parse_args()
    payload = build_public_payload(
        read_runs(args.input), args.ledger_issue, args.repository
    )
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
