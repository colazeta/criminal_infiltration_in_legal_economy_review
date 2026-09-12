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

The replacement terminal for ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4 had to be
created on 2026-09-12, because GitHub comments cannot be backdated. It therefore
cannot satisfy the ordinary same-Rome-date check even though it is immutable and
was created after the original run ended. A single exact comment-ID/batch-ID
recovery exception accepts that replacement while retaining every other temporal
and ledger-integrity check.

These historical comments remain on GitHub for audit, but must not enter the
active validated run set, public statistics, heartbeat state, or downstream
intake reconciliation.

This module does not weaken validation for any other run. It filters or relaxes
only the explicitly audited GitHub issue-comment IDs below before delegating to
the canonical validator.
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

LATE_RECOVERY_TERMINALS = {
    5647832949: {
        "batch_id": "ACADEMIC-2026-09-11-EXTRA-61e4d03af5c4",
        "run_date": "2026-09-11",
        "created_rome_date": "2026-09-12",
    }
}

_RAW_API_GET = _base.api_get
_RAW_VERIFY_LEDGER_COMMENT_TIME = _base.verify_ledger_comment_time


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


def _verify_ledger_comment_time_with_recovery(run: dict, comment: dict) -> None:
    recovery = LATE_RECOVERY_TERMINALS.get(comment.get("id"))
    if recovery is None:
        _RAW_VERIFY_LEDGER_COMMENT_TIME(run, comment)
        return

    if run.get("batch_id") != recovery["batch_id"] or run.get("run_date") != recovery["run_date"]:
        raise _base.MetricsError("late recovery terminal identity disagrees with recovery record")

    created = _base.parse_datetime(comment.get("created_at"), "ledger comment.created_at")
    updated = _base.parse_datetime(comment.get("updated_at"), "ledger comment.updated_at")
    ended = _base.parse_datetime(run.get("window_end"), "run.window_end")
    created_rome_date = created.astimezone(_base.ROME).date().isoformat()
    if (
        created != updated
        or created < ended
        or created_rome_date != recovery["created_rome_date"]
    ):
        raise _base.MetricsError(
            "late recovery terminal timestamps disagree with audited recovery record"
        )


def fetch_validated_runs(repository, ledger_issue, allowed_author, token, cycle=None):
    """Delegate to the canonical validator after exact recovery handling."""
    original_api = _base.api_get
    original_time = _base.verify_ledger_comment_time
    _base.api_get = _quarantine_api_get
    _base.verify_ledger_comment_time = _verify_ledger_comment_time_with_recovery
    try:
        return _base.fetch_validated_runs(
            repository, ledger_issue, allowed_author, token, cycle
        )
    finally:
        _base.api_get = original_api
        _base.verify_ledger_comment_time = original_time


api_get = _base.api_get
verify_intake_issue = _base.verify_intake_issue
extract_run = _base.extract_run


def main() -> None:
    original_api = _base.api_get
    original_time = _base.verify_ledger_comment_time
    _base.api_get = _quarantine_api_get
    _base.verify_ledger_comment_time = _verify_ledger_comment_time_with_recovery
    try:
        _base.main()
    finally:
        _base.api_get = original_api
        _base.verify_ledger_comment_time = original_time


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, _base.MetricsError, json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
