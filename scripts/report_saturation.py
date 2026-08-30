#!/usr/bin/env python3
"""Report whether complete review cycles meet the cautious numeric stop rule."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMPONENTS = {"database", "backward", "forward"}
CODE_FIELDS = (
    "new_theme_codes",
    "new_sector_codes",
    "new_mechanism_codes",
    "new_method_codes",
    "new_geography_codes",
    "new_outcome_codes",
)
REQUIRED_CONSECUTIVE_CYCLES = 3
THRESHOLD = 0.02


def number(value: str) -> float | None:
    value = (value or "").strip()
    if not value or value.upper() == "NA":
        return None
    return float(value)


def integer(value: str) -> int | None:
    parsed = number(value)
    if parsed is None or parsed < 0 or not parsed.is_integer():
        return None
    return int(parsed)


@dataclass(frozen=True)
class CycleAssessment:
    cycle_id: str
    completed_at: str
    complete: bool
    qualifying: bool
    eligible_increment_rate: float | None
    screening_yield: float | None
    reason: str


def assess_cycle(cycle_id: str, rows: list[dict[str, str]]) -> CycleAssessment:
    components = [(row.get("execution_type") or "").strip() for row in rows]
    completed_at = max((row.get("execution_date") or "").strip() for row in rows)
    complete = (
        set(components) == REQUIRED_COMPONENTS
        and len(components) == len(REQUIRED_COMPONENTS)
        and all((row.get("execution_status") or "").strip() == "completed" for row in rows)
    )
    if not complete:
        return CycleAssessment(
            cycle_id, completed_at, False, False, None, None, "incomplete cycle"
        )

    failures = [integer(row.get("unresolved_retrieval_failures", "")) for row in rows]
    new_eligible = [integer(row.get("new_eligible", "")) for row in rows]
    screened = [integer(row.get("unique_candidates_screened", "")) for row in rows]
    eligible_before = [integer(row.get("eligible_before", "")) for row in rows]
    code_counts = [integer(row.get(field, "")) for row in rows for field in CODE_FIELDS]
    if any(value is None for value in [*failures, *new_eligible, *screened, *eligible_before, *code_counts]):
        return CycleAssessment(
            cycle_id, completed_at, True, False, None, None, "missing or invalid metric"
        )

    assert all(value is not None for value in new_eligible)
    assert all(value is not None for value in screened)
    assert all(value is not None for value in eligible_before)
    total_new_eligible = sum(new_eligible)
    total_screened = sum(screened)
    baseline = min(eligible_before)
    increment_rate = total_new_eligible / baseline if baseline else None
    screening_yield = total_new_eligible / total_screened if total_screened else None
    if increment_rate is None or screening_yield is None:
        return CycleAssessment(
            cycle_id,
            completed_at,
            True,
            False,
            increment_rate,
            screening_yield,
            "undefined denominator",
        )

    no_failures = sum(failures) == 0
    no_new_codes = sum(code_counts) == 0
    qualifying = (
        increment_rate < THRESHOLD
        and screening_yield < THRESHOLD
        and no_failures
        and no_new_codes
    )
    reasons: list[str] = []
    if increment_rate >= THRESHOLD:
        reasons.append("eligible increment at or above 2%")
    if screening_yield >= THRESHOLD:
        reasons.append("screening yield at or above 2%")
    if not no_new_codes:
        reasons.append("new controlled codes")
    if not no_failures:
        reasons.append("unresolved retrieval failures")
    return CycleAssessment(
        cycle_id,
        completed_at,
        True,
        qualifying,
        increment_rate,
        screening_yield,
        "qualifies numerically" if qualifying else "; ".join(reasons),
    )


def assess_cycles(rows: list[dict[str, str]]) -> list[CycleAssessment]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        execution_id = (row.get("execution_id") or "").strip()
        cycle_id = (row.get("cycle_id") or "").strip()
        if execution_id.upper() == "E0":
            execution_type = (row.get("execution_type") or "").strip().lower()
            if execution_type != "seed" or cycle_id:
                raise ValueError(
                    "E0 must be the ungrouped seed execution; "
                    "it cannot represent a review-cycle component"
                )
            continue
        if not cycle_id:
            label = execution_id or "<missing execution_id>"
            raise ValueError(
                f"review execution {label!r} is missing cycle_id; "
                "only E0 may omit cycle_id"
            )
        grouped[cycle_id].append(row)
    assessments = [assess_cycle(cycle_id, grouped[cycle_id]) for cycle_id in grouped]
    return sorted(assessments, key=lambda item: (item.completed_at, item.cycle_id))


def trailing_qualifying(assessments: list[CycleAssessment]) -> int:
    trailing = 0
    for item in reversed(assessments):
        if not item.qualifying:
            break
        trailing += 1
    return trailing


def main() -> None:
    path = ROOT / "data/registry/execution_metrics.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assessments = assess_cycles(rows)
    trailing = trailing_qualifying(assessments)
    if trailing >= REQUIRED_CONSECUTIVE_CYCLES:
        print(
            f"[REVIEW REQUIRED] Numeric conditions hold for {trailing} consecutive "
            "complete cycles. A reviewer must still confirm frontier coverage and "
            "decide whether to stop."
        )
    else:
        print(
            f"[NOT SATURATED] {len(assessments)} recorded cycle(s); {trailing} "
            f"consecutive complete cycle(s) meet the numeric rule, "
            f"{REQUIRED_CONSECUTIVE_CYCLES} required."
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, ValueError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
