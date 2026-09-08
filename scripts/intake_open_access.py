"""Structured OA-1 intake attestations, never scientific/publication approvals.

No network inference: validate what an attributed discovery agent must actually
verify, then preserve that attestation independently of the mutable issue body.
"""
import csv
import json
import re
from datetime import datetime, time
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from scripts.open_access import validate_receipt

FIELDS = frozenset({"candidate_id", "full_text_url", "version_type", "host_type",
    "license_uri", "rights_basis", "rights_evidence_url", "access_status",
    "verification_method", "full_text_sha256", "verified_at"})
SNAPSHOT_FIELDS = frozenset({"schema_version", "batch_id", "source_issue_number",
    "source_body_sha256", "receipts"})
ROME = ZoneInfo("Europe/Rome")


def validate_access_origin(url):
    # sources.md authorises Zenodo record metadata AND files. Other listed
    # metadata APIs, DOI redirects and text readers do not authorise full bytes.
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "zenodo.org" or parsed.port not in (None, 443) or parsed.username or parsed.password:
        raise ValueError("OA evidence origin is not authorised for full-text/rights acquisition")


def validate_cycle(batch_date, issue_number, created_at, cycle):
    if batch_date < datetime.fromisoformat(cycle["daily_start_date"]).date() or int(issue_number) <= cycle["legacy_issue_ceiling"]:
        raise ValueError("intake belongs to the retired archive cycle")
    if created_at is None or created_at.tzinfo is None:
        raise ValueError("authenticated issue creation timestamp required")
    if created_at < datetime.fromisoformat(cycle["reset_at"].replace("Z", "+00:00")) or created_at.astimezone(ROME).date() != batch_date:
        raise ValueError("issue creation disagrees with archive cycle/batch")


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
    validate_access_origin(receipt["full_text_url"])
    validate_access_origin(receipt["rights_evidence_url"])
    if receipt["host_type"] != "repository":
        raise ValueError("authorised OA evidence host must be a repository")
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
        snapshot_semantics(snapshot)
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


def validate_snapshot_mapping(module, profile):
    """Check physical cardinality and explicit transformations, not slot names alone."""
    expected = {
        "schema_version": ("version", "decimal_string", "string"),
        "batch_id": ("event_id", "identity", "string"),
        "source_issue_number": ("was_derived_from", "github_issue_uri", "uriorcurie"),
        "source_body_sha256": ("v2_content_sha256", "identity", "string"),
    }
    for field, (slot, transform, range_name) in expected.items():
        mapping = module["snapshot_fields"][field]
        if mapping != {"slot": slot, "transform": transform, "range": range_name, "multivalued": False}:
            raise ValueError("incompatible snapshot transformation: " + field)
        semantic = profile["slots"][slot]
        if semantic.get("range", profile.get("default_range", "string")) != range_name or semantic.get("multivalued", False):
            raise ValueError("snapshot mapping range/cardinality mismatch: " + field)
    if module["snapshot_fields"]["receipts"] != {"containment": "AccessAssessment", "multivalued": True, "field_mapping": "receipt_fields"}:
        raise ValueError("receipt array must be structural AccessAssessment containment")
    for field, slot in module["receipt_fields"].items():
        semantic = profile["slots"][slot]
        range_name = semantic.get("range", profile.get("default_range", "string"))
        if semantic.get("multivalued", False) or range_name not in {"string", "OpenAccessVerificationEnum"}:
            raise ValueError("receipt field mapping is not scalar text: " + field)


def snapshot_semantics(snapshot):
    """Executable envelope mapping; no new scientific concepts or public export."""
    issue = snapshot["source_issue_number"]
    if type(issue) is not int or issue < 1 or type(snapshot["schema_version"]) is not int:
        raise ValueError("invalid physical snapshot identity")
    source = f"https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/{issue}"
    return {
        "version": str(snapshot["schema_version"]), "event_id": snapshot["batch_id"],
        "was_derived_from": source, "v2_content_sha256": snapshot["source_body_sha256"],
        "contained_assessments": [{"was_derived_from": source, "receipt": receipt} for receipt in snapshot["receipts"]],
    }
