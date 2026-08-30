from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from report_saturation import assess_cycles, trailing_qualifying  # noqa: E402


def execution(
    cycle_id: str,
    component: str,
    *,
    date: str = "2026-01-01",
    status: str = "completed",
    new_eligible: str = "0",
    eligible_before: str = "100",
    screened: str = "100",
    failures: str = "0",
    geography: str = "0",
    outcome: str = "0",
) -> dict[str, str]:
    return {
        "execution_id": f"{cycle_id}-{component}",
        "cycle_id": cycle_id,
        "execution_type": component,
        "execution_status": status,
        "execution_date": date,
        "new_eligible": new_eligible,
        "eligible_before": eligible_before,
        "unique_candidates_screened": screened,
        "unresolved_retrieval_failures": failures,
        "new_theme_codes": "0",
        "new_sector_codes": "0",
        "new_mechanism_codes": "0",
        "new_method_codes": "0",
        "new_geography_codes": geography,
        "new_outcome_codes": outcome,
    }


def cycle(cycle_id: str, date: str = "2026-01-01") -> list[dict[str, str]]:
    return [execution(cycle_id, component, date=date) for component in ("database", "backward", "forward")]


class SaturationCycleTests(unittest.TestCase):
    def test_three_executions_in_one_cycle_count_once(self) -> None:
        assessments = assess_cycles(cycle("R1"))
        self.assertEqual(1, len(assessments))
        self.assertEqual(1, trailing_qualifying(assessments))

    def test_three_complete_low_yield_cycles_require_review(self) -> None:
        rows = cycle("R1", "2026-01-01") + cycle("R2", "2026-02-01") + cycle("R3", "2026-03-01")
        self.assertEqual(3, trailing_qualifying(assess_cycles(rows)))

    def test_missing_forward_or_failed_component_breaks_sequence(self) -> None:
        rows = cycle("R1")[:2]
        self.assertFalse(assess_cycles(rows)[0].qualifying)
        rows = cycle("R1")
        rows[-1]["execution_status"] = "failed"
        self.assertFalse(assess_cycles(rows)[0].qualifying)

    def test_unresolved_failure_or_new_geography_outcome_disqualifies(self) -> None:
        rows = cycle("R1")
        rows[0]["unresolved_retrieval_failures"] = "1"
        self.assertFalse(assess_cycles(rows)[0].qualifying)
        rows = cycle("R1")
        rows[1]["new_geography_codes"] = "1"
        self.assertFalse(assess_cycles(rows)[0].qualifying)
        rows = cycle("R1")
        rows[2]["new_outcome_codes"] = "1"
        self.assertFalse(assess_cycles(rows)[0].qualifying)

    def test_exact_two_percent_and_zero_denominator_do_not_qualify(self) -> None:
        rows = cycle("R1")
        rows[0]["new_eligible"] = "2"
        self.assertFalse(assess_cycles(rows)[0].qualifying)
        rows = cycle("R1")
        for row in rows:
            row["eligible_before"] = "0"
        self.assertFalse(assess_cycles(rows)[0].qualifying)

    def test_latest_incomplete_cycle_breaks_trailing_streak(self) -> None:
        rows = cycle("R1", "2026-01-01") + cycle("R2", "2026-02-01") + cycle("R3", "2026-03-01")
        rows += cycle("R4", "2026-04-01")[:2]
        self.assertEqual(0, trailing_qualifying(assess_cycles(rows)))

    def test_malformed_metric_fails_loudly(self) -> None:
        rows = cycle("R1")
        rows[0]["new_eligible"] = "not-a-number"
        with self.assertRaises(ValueError):
            assess_cycles(rows)

    def test_row_order_does_not_change_cycle_order(self) -> None:
        rows = cycle("R2", "2026-02-01") + cycle("R1", "2026-01-01")
        rows.reverse()
        self.assertEqual(["R1", "R2"], [item.cycle_id for item in assess_cycles(rows)])


if __name__ == "__main__":
    unittest.main()
