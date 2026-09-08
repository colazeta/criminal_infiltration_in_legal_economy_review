"""Structured OA-1 intake attestations, never scientific/publication approvals.

No network inference: validate what an attributed discovery agent must actually
verify, then preserve that attestation independently of the mutable issue body.
"""
import csv
import json
import re
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.open_access import validate_receipt

FIELDS = frozenset({"candidate_id", "full_text_url", "version_type", "host_type",
    "license_uri", "rights_basis", "rights_evidence_url", "access_status",
    "verification_method", "full_text_sha256", "verified_at"})
SNAPSHOT_FIELDS = frozenset({"schema_version", "batch_id", "source_issue_number",
    "source_body_sha256", "receipts"})
ROME = ZoneInfo("Europe/Rome")


def validate_intake_access(receipt, candidate, batch_date, *, observed_by=None):
    if not isinstance(receipt, dict) or set(receipt) != FIELDS:
        raise ValueError("open_access requires the exact OA-1 receipt fields")
    for field, value in receipt.items():
        if not isinstance(value, str) or len(value) > (2000 if field == "rights_basis" else 1000):
            raise ValueError(f"open_access.{field}: bounded text required")
        if field != "license_uri" and not value.strip():
            raise ValueError(f"open_access.{field}: required")
    if receipt["candidate_id"] != candidate["candidate_id"]:
        raise ValueError("open_access receipt belongs to another candidate")
    if receipt["access_status"] != "verified_open":
        raise ValueError("open_access requires verified_open before intake")
    validate_receipt(receipt)
    if receipt["full_text_url"] not in candidate["source_links"]:
        raise ValueError("open_access full text must occur in candidate source_links")
    observed = datetime.fromisoformat(receipt["verified_at"].replace("Z", "+00:00"))
    deadline = observed_by or datetime.combine(batch_date, time.max, ROME)
    if observed > deadline:
        raise ValueError("open_access verification cannot follow the run")
    return receipt


def validate_snapshots(root: Path, queue=None):
    """Every active daily candidate retains one original, metadata-only receipt."""
    if queue is None:
        with (root / "data/curation/review_queue.csv").open(newline="", encoding="utf-8-sig") as handle:
            queue = list(csv.DictReader(handle))
    daily = {r["candidate_id"]: r for r in queue if r["origin"] == "daily_surveillance"}
    seen = set()
    for path in sorted((root / "data/curation/intake_access").glob("*.json")):
        snapshot = json.loads(path.read_text())
        if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_FIELDS:
            raise ValueError("invalid intake access snapshot fields")
        batch = snapshot["batch_id"]
        if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1:
            raise ValueError("invalid intake access snapshot version")
        if not isinstance(batch, str) or not re.fullmatch(r"ACADEMIC-\d{4}-\d{2}-\d{2}", batch) or path.name != batch + ".json":
            raise ValueError("invalid intake access snapshot batch")
        batch_date = datetime.strptime(batch.removeprefix("ACADEMIC-"), "%Y-%m-%d").date()
        if type(snapshot["source_issue_number"]) is not int or snapshot["source_issue_number"] < 1:
            raise ValueError("invalid intake access source issue")
        if not isinstance(snapshot["source_body_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", snapshot["source_body_sha256"]):
            raise ValueError("invalid intake source body checksum")
        receipts = snapshot["receipts"]
        if not isinstance(receipts, list) or not 1 <= len(receipts) <= 500:
            raise ValueError("invalid intake access receipt count")
        for receipt in receipts:
            cid = receipt.get("candidate_id") if isinstance(receipt, dict) else None
            if cid not in daily or cid in seen or not re.fullmatch(rf"CAND-{batch}-\d{{3}}", cid):
                raise ValueError("orphan or duplicate intake access receipt")
            row = daily[cid]
            if f"github-issue:#{snapshot['source_issue_number']};batch:{batch}" not in row["provenance"]:
                raise ValueError("intake access source disagrees with queue provenance")
            # Later metadata corrections may change queue links; the original
            # receipt is immutable and is not silently rewritten to follow them.
            validate_intake_access(receipt, {"candidate_id": cid, "source_links": [receipt.get("full_text_url")]}, batch_date)
            seen.add(cid)
    if seen != set(daily):
        raise ValueError("daily candidate missing preserved OA intake receipt")
    return len(seen)
