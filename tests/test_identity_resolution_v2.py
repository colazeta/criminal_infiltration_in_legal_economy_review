from __future__ import annotations

import unittest

from scripts.identity_resolution_v2 import (
    IdentityResolutionProtocolError,
    PROTOCOL,
    identity_key,
    observation_key,
    reduce_history,
    render_comments,
    validate,
    validate_against_history,
)


def payload(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "title": "Example scholarly work",
        "authors": ["Jane Example"],
        "url": "https://example.org/work",
        "doi": "10.1234/example.1",
        "year": 2026,
        "source_query_ids": ["PARALLEL-W1-Q1"],
        "status": "pending",
        "outcome": None,
        "candidate_id": None,
        "rationale": "Identity could not be closed conservatively in the scouting window.",
    }
    item.update(overrides)
    return {
        "protocol": PROTOCOL,
        "cycle_id": "2026-09-15-AM",
        "batch_id": "ACADEMIC-2026-09-15-EXTRA-test",
        "attempt": 2,
        "provider": "Parallel Search",
        "observed_at": "2026-09-15T09:20:00+00:00",
        "items": [item],
    }


class IdentityResolutionV2Tests(unittest.TestCase):
    def test_observation_and_identity_keys_are_distinct_concepts(self) -> None:
        first = validate(payload(), set())[0]
        second_payload = payload(url="https://repository.example/work")
        second_payload["provider"] = "Exa"
        second = validate(second_payload, set())[0]
        self.assertNotEqual(observation_key(first), observation_key(second))
        self.assertEqual(identity_key(first)[0], identity_key(second)[0])

    def test_first_record_must_be_pending(self) -> None:
        current = validate(payload(status="resolved", outcome="not_forwarded"), set())[0]
        with self.assertRaises(IdentityResolutionProtocolError):
            validate_against_history([], [current])

    def test_pending_can_resolve_known_record_only_when_candidate_exists(self) -> None:
        pending = validate(payload(), {"CAND-ACADEMIC-2026-09-15-001"})[0]
        resolved = validate(
            payload(
                status="resolved",
                outcome="known_exact_work",
                candidate_id="CAND-ACADEMIC-2026-09-15-001",
                rationale="DOI and primary metadata reconcile to the existing CandidateRecord.",
            ),
            {"CAND-ACADEMIC-2026-09-15-001"},
        )[0]
        validate_against_history([pending], [resolved])
        with self.assertRaises(IdentityResolutionProtocolError):
            validate(
                payload(
                    status="resolved",
                    outcome="known_exact_work",
                    candidate_id="CAND-ACADEMIC-2026-09-15-404",
                ),
                {"CAND-ACADEMIC-2026-09-15-001"},
            )

    def test_forwarded_to_intake_has_only_new_candidate_terminal(self) -> None:
        pending = validate(payload(), {"CAND-ACADEMIC-2026-09-15-001"})[0]
        forwarded = validate(
            payload(status="forwarded_to_intake", rationale="Identity is sufficiently distinct and has been handed to governed v3 intake."),
            {"CAND-ACADEMIC-2026-09-15-001"},
        )[0]
        validate_against_history([pending], [forwarded])
        known = validate(
            payload(
                status="resolved",
                outcome="known_exact_work",
                candidate_id="CAND-ACADEMIC-2026-09-15-001",
                rationale="This would be an invalid terminal after intake forwarding.",
            ),
            {"CAND-ACADEMIC-2026-09-15-001"},
        )[0]
        with self.assertRaises(IdentityResolutionProtocolError):
            validate_against_history([pending, forwarded], [known])
        new_candidate = validate(
            payload(
                status="resolved",
                outcome="new_candidate",
                candidate_id="CAND-ACADEMIC-2026-09-15-001",
                rationale="The normal v3 intake has now materialised the CandidateRecord.",
            ),
            {"CAND-ACADEMIC-2026-09-15-001"},
        )[0]
        validate_against_history([pending, forwarded], [new_candidate])

    def test_resolved_record_is_immutable(self) -> None:
        pending = validate(payload(), set())[0]
        resolved = validate(
            payload(status="resolved", outcome="not_forwarded", rationale="Primary verification shows this observation is outside the operational intake lane."),
            set(),
        )[0]
        state = reduce_history([pending, resolved])
        self.assertEqual(state[pending["observation_key"]]["outcome"], "not_forwarded")
        conflicting = dict(resolved)
        conflicting["rationale"] = "Changed terminal rationale."
        with self.assertRaises(IdentityResolutionProtocolError):
            validate_against_history([pending, resolved], [conflicting])

    def test_rendered_comment_carries_both_keys(self) -> None:
        item = validate(payload(), set())[0]
        comment = render_comments([item])[0]
        self.assertEqual(comment["observation_key"], item["observation_key"])
        self.assertEqual(comment["identity_key"], item["identity_key"])
        self.assertIn("cile-identity-resolution:2", comment["body"])


if __name__ == "__main__":
    unittest.main()
