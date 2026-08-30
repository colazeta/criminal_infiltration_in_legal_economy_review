#!/usr/bin/env python3
"""Validate repository structure, governance and release metadata."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    "INDEX.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "CITATION.cff",
    ".zenodo.json",
    "LICENSE",
    "docs/README.md",
    "docs/methodology/protocol.md",
    "docs/methodology/eligibility.md",
    "docs/methodology/discovery.md",
    "docs/methodology/expansion.md",
    "docs/methodology/saturation.md",
    "docs/methodology/reporting.md",
    "docs/governance/data-model.md",
    "docs/governance/sources.md",
    "docs/operations/automation.md",
    "docs/operations/release.md",
    "docs/operations/github-pages.md",
    "docs/history/e0-pilot.md",
    "data/registry/README.md",
    "schema/public-archive.schema.json",
    "scripts/build_archive.py",
    "scripts/report_saturation.py",
    "scripts/validation/validate_archive.py",
    "scripts/validation/validate_site.py",
    "site/index.html",
    "site/app.js",
    "site/styles.css",
    ".github/workflows/archive.yml",
)

REQUIRED_HEADERS = {
    "papers.csv": {
        "paper_id",
        "doi",
        "title",
        "authors",
        "year",
        "venue",
        "publisher",
        "document_type",
        "canonical_status",
    },
    "work_identifiers.csv": {
        "identifier_id",
        "paper_id",
        "scheme",
        "value",
        "relation",
        "is_primary",
        "verification_status",
    },
    "discovery_events.csv": {
        "event_id",
        "paper_id",
        "execution_id",
        "source_name",
        "source_platform",
        "query_string",
        "retrieval_status",
    },
    "screening_decisions.csv": {
        "decision_id",
        "paper_id",
        "screening_stage",
        "decision",
        "is_current",
    },
    "publications.csv": {
        "publication_id",
        "paper_id",
        "publication_version",
        "publication_status",
        "public_relevance_reason",
        "topic_code",
        "source_basis",
        "is_current",
        "supersedes_publication_id",
    },
    "taxonomy.csv": {"dimension", "code", "label", "taxonomy_version"},
    "paper_codes.csv": {"paper_id", "dimension", "code"},
    "editorial_summary.csv": {"snapshot_date", "is_current"},
    "archive_versions.csv": {
        "version",
        "protocol_version",
        "schema_version",
        "is_current",
    },
    "execution_metrics.csv": {
        "execution_id",
        "cycle_id",
        "execution_type",
        "execution_status",
        "unique_candidates_screened",
        "new_geography_codes",
        "new_outcome_codes",
        "unresolved_retrieval_failures",
    },
}

RETIRED_PATHS = (
    "WORKFLOW.md",
    "REVIEW_PROTOCOL.md",
    "docs/SYMPHONY_SETUP.md",
    "docs/NEXT_ACTION.md",
    "data/raw",
    "docs/executions",
    "scripts/00_setup_project.py",
    "scripts/01_seed_registry.py",
    "scripts/02_deduplicate_papers.py",
    "scripts/03_compute_saturation_metrics.py",
    "scripts/04_run_e0_identifier_first_search.py",
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def check_files() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        fail(f"Missing required files: {', '.join(missing)}")
    retired = [path for path in RETIRED_PATHS if (ROOT / path).exists()]
    if retired:
        fail(f"Retired paths returned to active tree: {', '.join(retired)}")


def check_registry_headers() -> None:
    for name, required in REQUIRED_HEADERS.items():
        path = ROOT / "data/registry" / name
        if not path.exists():
            fail(f"Missing registry: {name}")
        with path.open(newline="", encoding="utf-8-sig") as handle:
            headers = set(csv.DictReader(handle).fieldnames or [])
        missing = sorted(required - headers)
        if missing:
            fail(f"{name} missing column(s): {', '.join(missing)}")


def check_public_boundary() -> None:
    builder = (ROOT / "scripts/build_archive.py").read_text(encoding="utf-8")
    for forbidden in ("data/raw", "data/legacy", "candidate_outcomes", "promotion_audit"):
        if forbidden in builder:
            fail(f"Public builder refers to non-registry source: {forbidden}")
    for name in (
        "papers.csv",
        "work_identifiers.csv",
        "discovery_events.csv",
        "screening_decisions.csv",
        "publications.csv",
        "taxonomy.csv",
        "editorial_summary.csv",
        "archive_versions.csv",
    ):
        if name not in builder:
            fail(f"Public builder does not declare required registry {name}")


def check_issue_forms() -> None:
    paths = sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml"))
    forms = [path for path in paths if path.name != "config.yml"]
    if len(forms) < 4:
        fail("Expected at least four focused issue forms")
    for path in forms:
        text = path.read_text(encoding="utf-8")
        if re.search(r"^about:", text, re.M):
            fail(f"{path.name}: use description, not about")
        for key in ("name", "description", "title", "body"):
            if not re.search(rf"^{key}:", text, re.M):
                fail(f"{path.name}: missing top-level {key}")
        ids = re.findall(r"^\s+id:\s*([a-z0-9_-]+)\s*$", text, re.M)
        if len(ids) != len(set(ids)):
            fail(f"{path.name}: duplicate body id")


def check_actions_pinned() -> None:
    workflow = (ROOT / ".github/workflows/archive.yml").read_text(encoding="utf-8")
    uses = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.M)
    if not uses:
        fail("Archive workflow contains no actions")
    for action in uses:
        if not re.fullmatch(r"[^@]+@[0-9a-f]{40}", action):
            fail(f"GitHub Action is not pinned to a commit: {action}")
    safe_concurrency = (
        "concurrency:\n"
        "  group: archive-${{ github.workflow }}-${{ github.ref }}\n"
        "  cancel-in-progress: true"
    )
    if safe_concurrency not in workflow:
        fail("Archive workflow must cancel superseded runs for the same ref")


def check_release_metadata() -> None:
    with (ROOT / "data/registry/archive_versions.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        versions = list(csv.DictReader(handle))
    current = [row for row in versions if row.get("is_current", "").lower() == "true"]
    if len(current) != 1:
        fail("archive_versions.csv must have one current row")
    version = current[0]["version"]
    release_date = current[0]["release_date"]
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f"version: {version}" not in cff or f"date-released: {release_date}" not in cff:
        fail("CITATION.cff disagrees with archive_versions.csv")
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    if zenodo.get("version") != version or zenodo.get("publication_date") != release_date:
        fail(".zenodo.json disagrees with archive_versions.csv")
    if f"## [{version}] - {release_date}" not in (ROOT / "CHANGELOG.md").read_text(
        encoding="utf-8"
    ):
        fail("CHANGELOG.md lacks the current version/date")


def check_governance_copy() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
    for phrase in ("never auto-merge", "intake issue", "publication gate"):
        if phrase not in agents:
            fail(f"AGENTS.md missing governance phrase: {phrase}")
    sources = (ROOT / "docs/governance/sources.md").read_text(encoding="utf-8")
    for source in ("Scite", "Exa Search", "GitHub"):
        if source not in sources:
            fail(f"Source governance missing {source}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    if "living curated evidence map" not in readme:
        fail("README must preserve the living-archive limitation")
    expansion = (ROOT / "docs/methodology/expansion.md").read_text(
        encoding="utf-8"
    ).lower()
    for phrase in (
        "known-item calibration",
        "source/query marginal yield",
        "backward and forward citation",
        "independent curator decision",
    ):
        if phrase not in expansion:
            fail(f"Expansion strategy missing safeguard: {phrase}")
    pages = (ROOT / "docs/operations/github-pages.md").read_text(
        encoding="utf-8"
    )
    for phrase in ("GitHub Actions", ".github/workflows/archive.yml", "site/"):
        if phrase not in pages:
            fail(f"GitHub Pages guide missing deployment element: {phrase}")


def main() -> None:
    check_files()
    check_registry_headers()
    check_public_boundary()
    check_issue_forms()
    check_actions_pinned()
    check_release_metadata()
    check_governance_copy()
    print("[OK] Repository structure, governance and release metadata passed.")


if __name__ == "__main__":
    try:
        main()
    except (csv.Error, json.JSONDecodeError, OSError) as exc:
        fail(str(exc))
