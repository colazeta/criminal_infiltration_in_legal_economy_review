#!/usr/bin/env python3
"""Read the governed surveillance ledger while quarantining audited invalid batches.

The batches ACADEMIC-2026-09-11-EXTRA-2520dfa54e12 and
ACADEMIC-2026-09-11-EXTRA-f28583e91573 were later proven to repeat candidate
identities already present in earlier intake state. The original terminal for
ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4 was accidentally edited during an
authorised recovery and therefore lost append-only validity.

Six later immutable v3 terminals are also quarantined because their source
``limitations`` field contains a text item longer than the schema's 180-character
maximum. Their scientific/intake content is not being withdrawn; each is replaced
by a separately appended terminal with the same governed counts and references
and a schema-valid shortened limitation.

These historical comments remain on GitHub for audit, but must not enter the
active validated run set, public statistics, heartbeat state, or downstream
intake reconciliation.

This module does not weaken validation for any other run. It filters only the
explicitly audited GitHub issue-comment IDs below before delegating to the
canonical validator.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError

import fetch_surveillance_ledger as _base


QUARANTINED_LEDGER_COMMENTS = {
    5631393628: "ACADEMIC-2026-09-11-EXTRA-2520dfa54e12",
    5639689529: "ACADEMIC-2026-09-11-EXTRA-f28583e91573",
    5633517951: "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
    5641872719: "ACADEMIC-2026-09-12-EXTRA-724679219793",
    5643146365: "ACADEMIC-2026-09-12-EXTRA-4faa0ba491c4",
    5643786921: "ACADEMIC-2026-09-12-EXTRA-9bdb3c1e67c7",
    5644330070: "ACADEMIC-2026-09-12-EXTRA-d6b0ffff25fd",
    5644553677: "ACADEMIC-2026-09-12-EXTRA-335f7df7ae34",
    5646294694: "ACADEMIC-2026-09-12-EXTRA-570dae192194",
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
