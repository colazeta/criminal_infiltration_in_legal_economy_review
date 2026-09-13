#!/usr/bin/env python3
"""Prepare/check existing reading support without an external full-queue backfill.

This is not a scheduler or scientific approval route. It invokes only existing
mechanical bridges/builders; repository writes still need a reviewed green PR.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_INPUTS = {
    "data/curation/reading_aids.json",
    "data/curation/reading_aid_overrides.json",
    "data/curation/retrieval_coverage.csv",
    "data/curation/abstract_coverage.csv",
}
BUILDERS = [
    ["python3", "scripts/build_archive.py"],
    ["python3", "scripts/build_secondary_collections.py"],
    ["python3", "scripts/metrics/build_research_stats.py"],
    ["python3", "scripts/curation/build_curator_stats.py"],
    ["python3", "scripts/curation/build_curator_options.py"],
]
PREPARE = [
    ["python3", "scripts/retrieval/apply_verified_reading_locators.py"],
    ["node", "scripts/abstracts/promote_verified_sources.mjs"],
    *BUILDERS,
]
MANDATORY = [
    ["python3", "scripts/validation/validate_repository.py"],
    ["python3", "scripts/ontology/validate_ontology.py"],
    ["python3", "scripts/ontology/build_model_browser.py"],
    ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
    ["python3", "scripts/build_archive.py"],
    ["python3", "scripts/build_secondary_collections.py"],
    ["python3", "scripts/curation/build_curator_stats.py"],
    ["python3", "scripts/curation/build_curator_options.py"],
    ["python3", "scripts/validation/validate_archive.py"],
    ["python3", "scripts/validation/validate_site.py"],
    *[["node", "--check", file] for file in (
        "site/app.js", "site/aml.js", "site/stats.js", "site/curator.js",
        "site/curator-config.js", "site/curator-guided.js", "site/model.js",
        "site/review-v2.js", "curator-app/src/index.js", "curator-app/src/worker.js",
    )],
    ["node", "--test", "curator-app/test/*.test.js"],
    ["python3", "scripts/report_saturation.py"],
]


def refresh_mode(event: str, before: str, changed: list[str]) -> str:
    """Unknown/truncated history and queue/implementation changes require full mode."""
    if event != "push" or not re.fullmatch(r"[0-9a-f]{40}", before) or set(before) == {"0"}:
        return "full"
    if not changed:
        return "full"
    for name in changed:
        if name not in LOCAL_INPUTS and not name.startswith(("site/data/", "docs/", "tests/")):
            return "full"
    return "local"


def event_refresh_mode(root: Path = ROOT) -> str:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        before = event.get("before", "")
        if not re.fullmatch(r"[0-9a-f]{40}", before) or set(before) == {"0"}:
            return "full"
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", before, "HEAD"], cwd=root, text=True
        ).splitlines()
        return refresh_mode(os.environ.get("GITHUB_EVENT_NAME", ""), before, changed)
    except (KeyError, OSError, ValueError, TypeError, subprocess.CalledProcessError):
        return "full"


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def index_rows(rows: list[dict], key: str, name: str) -> dict[str, dict]:
    counts = Counter(row.get(key) for row in rows)
    if any(not value or count != 1 for value, count in counts.items()):
        raise ValueError(f"{name}: missing or duplicate identity")
    return {row[key]: row for row in rows}


def audit(root: Path = ROOT) -> dict:
    """Read whole public tables. Locators and curator support are not private evidence."""
    curation = root / "data/curation"
    queue = index_rows(csv_rows(curation / "review_queue.csv"), "candidate_id", "queue")
    register = index_rows(json.loads((root / "site/data/paper-register.json").read_text())["records"], "id", "register")
    stats = json.loads((root / "site/data/curator-stats.json").read_text())
    retrieval = index_rows(csv_rows(curation / "retrieval_coverage.csv"), "candidate_id", "retrieval")
    abstracts = index_rows(csv_rows(curation / "abstract_coverage.csv"), "candidate_id", "abstracts")
    overrides = index_rows(json.loads((curation / "reading_aid_overrides.json").read_text())["records"], "candidateId", "overrides")
    errors = []
    if set(queue) != set(register):
        errors.append("public_register_identity_drift")
    if stats.get("totalMaterialised") != len(queue):
        errors.append("curator_stats_count_drift")
    if set(overrides) - set(queue):
        errors.append("unregistered_reading_override")
    verified = 0
    represented = 0
    for cid, aid in overrides.items():
        if aid.get("kind") != "full_text_intro" or "Evidence basis: full_text" not in aid.get("note", ""):
            continue
        verified += 1
        row = retrieval.get(cid, {})
        urls = [url.strip() for url in row.get("source_urls", "").split(";")]
        if row.get("resolution_status") == "full_text" and aid.get("sourceUrl") in urls:
            represented += 1
        else:
            errors.append(f"verified_locator_not_materialised:{cid}")
    verified_abstracts = 0
    represented_abstracts = 0
    for cid, aid in overrides.items():
        if aid.get("kind") == "verified_abstract_source":
            verified_abstracts += 1
            if abstracts.get(cid, {}).get("coverage_status") == "available":
                represented_abstracts += 1
            else:
                errors.append(f"verified_abstract_not_materialised:{cid}")
    return {
        "queue_records": len(queue), "public_register_records": len(register),
        "curator_stats_records": stats.get("totalMaterialised"),
        "retrieval_rows": len(retrieval), "abstract_rows": len(abstracts),
        "missing_retrieval_rows": len(set(queue) - set(retrieval)),
        "missing_abstract_rows": len(set(queue) - set(abstracts)),
        "reading_overrides": len(overrides),
        "verified_full_text_overrides": verified,
        "materialised_verified_locators": represented,
        "verified_abstract_overrides": verified_abstracts,
        "materialised_verified_abstracts": represented_abstracts,
        "retrieval_status_counts": dict(sorted(Counter(r.get("resolution_status", "") for r in retrieval.values()).items())),
        "abstract_status_counts": dict(sorted(Counter(r.get("coverage_status", "") for r in abstracts.values()).items())),
        "private_sources_inspected": False, "scientific_approval_inferred": False,
        "errors": errors,
    }


def run_commands(commands: list[list[str]], root: Path = ROOT) -> None:
    for command in commands:
        expanded = list(command)
        if expanded[:2] == ["node", "--test"]:
            tests = sorted(str(path.relative_to(root)) for path in root.glob(expanded[2]))
            if not tests:
                raise ValueError("mandatory_node_tests_missing")
            expanded = expanded[:2] + tests
        print("Running: " + " ".join(expanded), flush=True)
        subprocess.run(expanded, cwd=root, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Apply existing bridges and deterministic builders on the current branch")
    parser.add_argument("--validate", action="store_true", help="Run the full AGENTS.md mandatory block; never push/merge")
    parser.add_argument("--check", action="store_true", help="Read-only public delivery audit (the default)")
    parser.add_argument("--refresh-mode", action="store_true", help="Classify current push as local/full; unknown history fails to full")
    parser.add_argument("--summary", type=Path, help="Optional ephemeral workflow summary, never a private evidence receipt")
    args = parser.parse_args()
    if args.refresh_mode:
        if args.prepare or args.validate or args.check or args.summary:
            parser.error("--refresh-mode must be used alone")
        print(event_refresh_mode())
        return
    if args.check and (args.prepare or args.validate):
        parser.error("--check is read-only; do not combine it with --prepare/--validate")
    if args.prepare:
        run_commands(PREPARE)
    if args.validate:
        run_commands(MANDATORY)
    report = audit()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.summary:
        args.summary.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["errors"]:
        raise SystemExit("selected_paper_delivery_incomplete")


if __name__ == "__main__":
    main()
