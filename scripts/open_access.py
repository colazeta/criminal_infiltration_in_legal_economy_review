"""Fail-closed OA publication gate, separate from scientific screening.

Only reviewed manifestation-level access receipts are read. A locator or an
aggregator's is_oa flag cannot manufacture a receipt. History is append-only.
"""
import re
from datetime import datetime
from urllib.parse import urlsplit

FIELDS = ("assessment_id", "paper_id", "full_text_url", "version_type", "host_type",
          "license_uri", "rights_basis", "rights_evidence_url", "access_status",
          "verification_method", "full_text_sha256", "verified_at", "supersedes_id")
STATUSES = {"verified_open", "restricted", "unknown", "revoked"}
VERSIONS = {"accepted", "version_of_record"}


def safe_url(value):
    try:
        url = urlsplit(value)
        return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
    except ValueError:
        return False


def validate_receipt(row):
    if row.get("access_status") not in STATUSES:
        raise ValueError("invalid open-access status")
    try:
        observed = datetime.fromisoformat(row["verified_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("timezone missing")
    except (ValueError, KeyError):
        raise ValueError("open-access verification requires an explicit timestamp and timezone") from None
    if row["access_status"] != "verified_open":
        return
    if row.get("version_type") not in VERSIONS or row.get("host_type") not in {"publisher", "repository"}:
        raise ValueError("open-access publication version or host is not verified")
    if not all(safe_url(row.get(k, "")) for k in ("full_text_url", "rights_evidence_url")):
        raise ValueError("open-access full text and rights evidence require HTTPS locators")
    if row.get("license_uri") and not safe_url(row["license_uri"]):
        raise ValueError("invalid open-access licence URI")
    if not row.get("rights_basis", "").strip() or row.get("verification_method") != "anonymous_full_text_verified":
        raise ValueError("lawful anonymous full-text verification is required")
    if not re.fullmatch(r"[a-f0-9]{64}", row.get("full_text_sha256", "")):
        raise ValueError("open-access full-text checksum required")


def current_receipts(rows):
    by_id, children, roots = {}, {}, {}
    for row in rows or []:
        validate_receipt(row)
        aid, paper = row.get("assessment_id"), row.get("paper_id")
        if not aid or aid in by_id or not paper:
            raise ValueError("duplicate or missing open-access assessment identity")
        by_id[aid] = row
        parent = row.get("supersedes_id")
        if parent:
            if parent in children:
                raise ValueError("branched open-access assessment history")
            children[parent] = aid
        elif paper in roots:
            raise ValueError("multiple open-access assessment roots")
        else:
            roots[paper] = aid
    for row in by_id.values():
        parent = row.get("supersedes_id")
        if parent and (parent not in by_id or by_id[parent]["paper_id"] != row["paper_id"]):
            raise ValueError("orphan or cross-work open-access supersession")
    result, visited = {}, set()
    for paper, aid in roots.items():
        while aid:
            if aid in visited:
                raise ValueError("cyclic open-access history")
            visited.add(aid)
            result[paper] = by_id[aid]
            aid = children.get(aid)
    if visited != set(by_id):
        raise ValueError("disconnected open-access history")
    return result


def public_access(row):
    if not row or row.get("access_status") != "verified_open":
        raise ValueError("verified open-access full text required for publication")
    validate_receipt(row)
    return {"status": "verified_open", "fullTextUrl": row["full_text_url"],
            "version": row["version_type"], "host": row["host_type"],
            "licence": row.get("license_uri") or None, "verifiedAt": row["verified_at"]}
