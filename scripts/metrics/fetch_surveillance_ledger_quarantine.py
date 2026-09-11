#!/usr/bin/env python3
"""Read the governed surveillance ledger while quarantining one invalid batch.

The batch ACADEMIC-2026-09-11-EXTRA-2520dfa54e12 was later proven to repeat
candidate identities already present in intake #226. Its immutable terminal
comment must remain available for audit, but it must not enter the active
validated run set, public statistics, heartbeat state, or downstream intake
reconciliation.

This module does not weaken validation for any other run. It filters exactly one
immutable GitHub issue-comment ID before delegating to the canonical validator.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError

import fetch_surveillance_ledger as _base


QUARANTINED_LEDGER_COMMENTS = {
    5631393628: "ACADEMIC-2026-09-11-EXTRA-2520dfa54e12",
}
_RAW_API_GET = _base.api_get


def _quarantine_api_get(url: str, token: str):
    payload, links = _RAW_API_GET(url, token)
    if isinstance(payload, list) and "/issues/30/comments" in url:
        kept = []
        for item in payload:
            comment_id = item.get("id") if isinstance(item, dict) else None
            expected_batch = QUARANTINED_LEDGER_COMMENTS.get(comment_id)
            if expected_batch is None:
                kept.append(item)
                continue
            body = str(item.get("body") or "")
            if expected_batch not in body:
                raise _base.MetricsError(
                    "quarantined ledger comment identity disagrees with recovery record"
                )
        payload = kept
    return payload, links


def fetch_validated_runs(repository, ledger_issue, allowed_author, token, cycle=None):
    """Delegate to the canonical validator after exact comment quarantine."""
    original = _base.api_get
    _base.api_get = _quarantine_api_get
    try:
        return _base.fetch_validated_runs(
            repository, ledger_issue, allowed_author, token, cycle
        )
    finally:
        _base.api_get = original


# Callers that need to validate the live intake object still use the canonical
# functions directly. Only ledger enumeration is quarantined.
api_get = _base.api_get
verify_intake_issue = _base.verify_intake_issue
extract_run = _base.extract_run


def main() -> None:
    original = _base.api_get
    _base.api_get = _quarantine_api_get
    try:
        _base.main()
    finally:
        _base.api_get = original


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, _base.MetricsError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
