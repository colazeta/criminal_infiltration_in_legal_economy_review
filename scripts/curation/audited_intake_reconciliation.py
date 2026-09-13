"""Read-only, evidence-pinned occurrence reconciliation for historical intake 225.

This does not create candidates, canonical identities or a missing run terminal.
The owner-reviewed evidence and rollback are in residual-intake-recovery.md.
No title similarity, parent-book identifier or filename is a general match rule.
"""
from __future__ import annotations

import hashlib
import json

from scripts.curation.import_intake_issue import IntakeImportError

BATCH = "ACADEMIC-2026-09-09-EXTRA-4d1777fe93be"
SOURCE_BODY_SHA256 = "2851f8e186032f7bf13c015c8f9c83670ee41a5e2558cc1949682c9dbe5163bd"
IDENTITY_FIELDS = (
    "candidate_id", "title", "authors", "year", "venue", "doi",
    "other_identifiers", "source_links",
)
AUDITED_OCCURRENCES = {
    f"CAND-{BATCH}-006": (
        "CAND-ACADEMIC-2026-09-13-EXTRA-a6766e6649ed-004",
        "0245d0a7781372a6a23c62759f127e08dc18a96877980bb6a8503d37f8bb64d1",
        "https://unicri.org/services/library_documentation/publications/unicri_series",
    ),
    f"CAND-{BATCH}-011": (
        "CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-024",
        "4d18c643e92297788add7264c16d276268f9d86c748f98d43164b183a970ae86",
        "https://www.routledge.com/Organised-Crime-in-European-Businesses/"
        "Savona-Riccardi-Berlusconi/p/book/9781138499478",
    ),
}


def identity_fingerprint(row: dict) -> str:
    identity = {field: row.get(field, "") for field in IDENTITY_FIELDS}
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audited_occurrences(issue: dict, queue: list[dict], candidates: list[dict]):
    """Return exact audited occurrences and unhandled source candidates.

    Changed evidence or target metadata fails closed for this historical issue.
    Other issues receive no special treatment. The caller must still reconcile
    every remaining candidate, including 003, before finalising the intake.
    """
    if issue.get("number") != 225:
        return list(candidates), []
    if (issue.get("user") or {}).get("login") != "colazeta":
        raise IntakeImportError("audited intake reconciliation requires its original owner")
    if issue.get("title") != f"[INTAKE][ACADEMIC] {BATCH}":
        raise IntakeImportError("audited intake reconciliation title changed")
    body = issue.get("body")
    if not isinstance(body, str) or hashlib.sha256(body.encode("utf-8")).hexdigest() != SOURCE_BODY_SHA256:
        raise IntakeImportError("audited intake reconciliation source evidence changed")
    remaining, skipped = [], []
    for candidate in candidates:
        source_id = candidate["candidate_id"]
        receipt = AUDITED_OCCURRENCES.get(source_id)
        if receipt is None:
            remaining.append(candidate)
            continue
        target_id, expected_fingerprint, evidence_url = receipt
        targets = [row for row in queue if row.get("candidate_id") == target_id]
        if len(targets) != 1 or identity_fingerprint(targets[0]) != expected_fingerprint:
            raise IntakeImportError(f"audited intake target absent, ambiguous or changed: {target_id}")
        skipped.append({
            "candidate_id": source_id,
            "existing_ids": [f"candidate:{target_id}"],
            "matched_keys": [f"audited-source-occurrence:225:{source_id}", evidence_url],
            "title_variant": False,
        })
    return remaining, skipped
