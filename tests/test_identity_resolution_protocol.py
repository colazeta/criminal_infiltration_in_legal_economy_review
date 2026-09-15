from __future__ import annotations

import json
import unittest

from scripts.identity_resolution import (
    IdentityResolutionProtocolError,
    PROTOCOL,
    render_comments,
    stable_key,
    validate,
)


def payload(**item_overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "title": "Example scholarly work",
        "url": "https://example.org/work",
        "doi": "10.1234/example.1",
        "year": 2026,
        "source_query_ids": ["PARALLEL-W1-Q1"],
        "status": "pending",
        "outcome": None,
        "candidate_id": None,
        "rationale": "Identity could not be resolved conservatively during the completed scouting window.",
    }
    item.update(item_overrides)
    return {
        "protocol": PROTOCOL,
        "cycle_id": "2026-09-15-AM",
        "batch_id": "ACADEMIC-2026-09-15-EXTRA-test",
        "attempt": 2,
        "provider": "Parallel Search",
        "observed_at": "2026-09-15T09:20:00+00:00",
        "items": [item],
    }


class IdentityResolutionProtocolTests(unittest.TestCase):
    def test_pending_identity_renders_durable_comment(self) -> None:
        items = validate(payload())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "pending")
        comments = render_comments(items)
        self.assertEqual(len(comments), 1)
        self.assertIn("cile-identity-resolution:1", comments[0]["body"])
        self.assertEqual(comments[0]["identity_key"], items[0]["identity_key"])

    def test_resolved_known_work_requires_candidate_id(self) -> None:
        with self.assertRaises(IdentityResolutionProtocolError):
            validate(payload(status="resolved", outcome="known_exact_work", candidate_id=None))
        items = validate(
            payload(
                status="resolved",
                outcome="known_exact_work",
                candidate_id="CAND-ACADEMIC-2026-09-08-001",
                rationale="DOI and title/year now reconcile to the existing CandidateRecord.",
            )
        )
        self.assertEqual(items[0]["outcome"], "known_exact_work")

    def test_not_forwarded_cannot_carry_candidate_id(self) -> None:
        with self.assertRaises(IdentityResolutionProtocolError):
            validate(
                payload(
                    status="resolved",
                    outcome="not_forwarded",
                    candidate_id="CAND-ACADEMIC-2026-09-08-001",
                )
            )

    def test_new_candidate_requires_governed_candidate_id(self) -> None:
        items = validate(
            payload(
                status="resolved",
                outcome="new_candidate",
                candidate_id="CAND-ACADEMIC-2026-09-15-001",
                rationale="The normal governed intake path has already materialised this CandidateRecord.",
            )
        )
        self.assertEqual(items[0]["candidate_id"], "CAND-ACADEMIC-2026-09-15-001")

    def test_explicit_identity_key_must_match_bibliographic_identity(self) -> None:
        base = payload()
        validated = validate(base)[0]
        good = payload(identity_key=validated["identity_key"])
        self.assertEqual(validate(good)[0]["identity_key"], validated["identity_key"])
        with self.assertRaises(IdentityResolutionProtocolError):
            validate(payload(identity_key="0" * 64))

    def test_identity_key_is_stable_across_pending_and_resolution_state(self) -> None:
        pending = validate(payload())[0]
        resolved = validate(
            payload(
                status="resolved",
                outcome="not_forwarded",
                candidate_id=None,
                rationale="Primary-source verification established that the result is not a scholarly work for this lane.",
            )
        )[0]
        self.assertEqual(stable_key(pending), stable_key(resolved))

    def test_http_url_is_rejected(self) -> None:
        with self.assertRaises(IdentityResolutionProtocolError):
            validate(payload(url="http://example.org/work"))


if __name__ == "__main__":
    unittest.main()
