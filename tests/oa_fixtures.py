"""Synthetic metadata-only receipts. Never evidence about a real paper."""
import hashlib


def synthetic_oa(candidate_id, full_text_url, day):
    return {
        "candidate_id": candidate_id, "full_text_url": full_text_url,
        "version_type": "version_of_record", "host_type": "repository",
        "license_uri": "", "rights_basis": "Synthetic authorised-deposit fixture; no real verification.",
        "rights_evidence_url": "https://example.org/synthetic-rights",
        "access_status": "verified_open", "verification_method": "anonymous_full_text_verified",
        "full_text_sha256": hashlib.sha256(b"Synthetic full-text fixture").hexdigest(),
        "verified_at": f"{day}T00:00:00Z",
    }
