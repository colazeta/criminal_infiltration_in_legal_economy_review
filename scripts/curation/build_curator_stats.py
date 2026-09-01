#!/usr/bin/env python3
"""Build the closed, aggregate-only public projection of the curator queue."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_STATUSES = {"pending", "needs_full_text"}
STAGE_KEYS = {
    "metadata_fix": "metadataFix",
    "manual_review": "manualReview",
    "abstract_full_text_review": "abstractReview",
    "legacy_rejection_review": "legacyRejectionReview",
}
SECONDARY_COLLECTION_KEYS = {
    "broader_aml": "broaderAml",
}


class CuratorStatsError(ValueError):
    """Raised when a safe aggregate cannot be built from the governed queue."""


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CuratorStatsError(f"{path.name} has no header")
        return [dict(row) for row in reader]


def build_payload(root: Path = ROOT) -> dict[str, object]:
    queue = read_rows(root / "data" / "curation" / "review_queue.csv")
    actions = read_rows(root / "data" / "curation" / "actions.csv")
    candidate_ids = [row.get("candidate_id", "") for row in queue]
    if not queue or "" in candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
        raise CuratorStatsError("Curator queue candidate IDs are empty or duplicated")

    by_stage = {value: 0 for value in STAGE_KEYS.values()}
    open_by_origin = {"legacy": 0, "daily": 0}
    by_secondary_collection = {
        value: 0 for value in SECONDARY_COLLECTION_KEYS.values()
    }
    open_count = 0
    for row in queue:
        status = row.get("current_status", "")
        secondary_collection = row.get("secondary_collection_code", "")
        if secondary_collection:
            if secondary_collection not in SECONDARY_COLLECTION_KEYS:
                raise CuratorStatsError(
                    "Unknown secondary collection for "
                    f"{row.get('candidate_id', 'candidate')}"
                )
            if status in ACTIVE_STATUSES:
                raise CuratorStatsError(
                    "An open candidate cannot already be routed to a secondary "
                    f"collection: {row.get('candidate_id', 'candidate')}"
                )
            by_secondary_collection[
                SECONDARY_COLLECTION_KEYS[secondary_collection]
            ] += 1
        if status not in ACTIVE_STATUSES:
            continue
        open_count += 1
        stage = (
            "abstract_full_text_review"
            if status == "needs_full_text"
            else row.get("review_stage", "")
        )
        if stage not in STAGE_KEYS:
            raise CuratorStatsError(
                f"Unknown active review stage for {row.get('candidate_id', 'candidate')}"
            )
        by_stage[STAGE_KEYS[stage]] += 1
        origin = row.get("origin", "")
        if origin == "daily_surveillance":
            open_by_origin["daily"] += 1
        elif origin.startswith("legacy_"):
            open_by_origin["legacy"] += 1
        else:
            raise CuratorStatsError(
                f"Unknown active origin for {row.get('candidate_id', 'candidate')}"
            )

    return {
        "schemaVersion": 2,
        "totalMaterialised": len(queue),
        "open": open_count,
        "completed": len(queue) - open_count,
        "actionCount": len(actions),
        "byStage": by_stage,
        "openByOrigin": open_by_origin,
        "bySecondaryCollection": by_secondary_collection,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path; defaults to site/data/curator-stats.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    output = args.output or root / "site" / "data" / "curator-stats.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(root)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"[OK] Wrote aggregate curator stats: {payload['open']} open, "
        f"{payload['completed']} completed."
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, csv.Error, CuratorStatsError) as exc:
        raise SystemExit(f"[FAIL] {exc}") from exc
