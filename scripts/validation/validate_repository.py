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
    "docs/GUIDA_RAPIDA_IT.md",
    "docs/methodology/protocol.md",
    "docs/methodology/eligibility.md",
    "docs/methodology/discovery.md",
    "docs/methodology/expansion.md",
    "docs/methodology/expansion-reference.md",
    "docs/methodology/saturation.md",
    "docs/methodology/reporting.md",
    "docs/governance/data-model.md",
    "docs/governance/sources.md",
    "docs/operations/automation.md",
    "docs/operations/daily-metrics.md",
    "docs/operations/curation.md",
    "docs/operations/release.md",
    "docs/operations/github-pages.md",
    "docs/history/e0-pilot.md",
    "data/registry/README.md",
    "schema/public-archive.schema.json",
    "schema/surveillance-run.schema.json",
    "schema/research-stats.schema.json",
    "scripts/build_archive.py",
    "scripts/metrics/build_research_stats.py",
    "scripts/metrics/fetch_surveillance_ledger.py",
    "scripts/metrics/surveillance.py",
    "scripts/report_saturation.py",
    "scripts/curation/apply_action.py",
    "scripts/validation/validate_archive.py",
    "scripts/validation/validate_site.py",
    "site/index.html",
    "site/curate.html",
    "site/stats.html",
    "site/app.js",
    "site/stats.js",
    "site/styles.css",
    "site/data/research-stats.json",
    ".github/workflows/archive.yml",
    ".github/workflows/curation.yml",
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
    "paper_codes.csv": {
        "coding_id",
        "paper_id",
        "dimension",
        "code",
        "coding_version",
        "is_current",
        "supersedes_coding_id",
    },
    "exclusion_reasons.csv": {"code", "label", "definition"},
    "work_relations.csv": {
        "relation_id",
        "source_paper_id",
        "target_paper_id",
        "relation",
        "reason",
        "evidence",
        "curator",
        "decided_at",
    },
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
    metrics_builder = (ROOT / "scripts/metrics/surveillance.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "data/registry",
        "data/legacy",
        "candidate_outcomes",
        "screening_decisions.csv",
    ):
        if forbidden in metrics_builder:
            fail(f"Daily metrics builder crosses its aggregate boundary: {forbidden}")


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
    workflow_paths = sorted((ROOT / ".github/workflows").glob("*.yml"))
    if not workflow_paths:
        fail("No GitHub Actions workflows found")
    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        uses = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.M)
        if not uses:
            fail(f"{path.name}: workflow contains no actions")
        for action in uses:
            if not re.fullmatch(r"[^@]+@[0-9a-f]{40}", action):
                fail(f"{path.name}: action is not pinned to a commit: {action}")
    workflow = (ROOT / ".github/workflows/archive.yml").read_text(encoding="utf-8")
    safe_concurrency = (
        "concurrency:\n"
        "  group: archive-${{ github.workflow }}-${{ github.ref }}\n"
        "  cancel-in-progress: true"
    )
    if safe_concurrency not in workflow:
        fail("Archive workflow must cancel superseded runs for the same ref")
    for phrase in (
        'cron: "30 6 * * *"',
        "issues: read",
        "fetch_surveillance_ledger.py",
        "build_research_stats.py",
        "--issue 30",
        '--allowed-author "$LEDGER_AUTHOR"',
        "node --check site/stats.js",
    ):
        if phrase not in workflow:
            fail(f"Archive workflow missing daily-metrics safeguard: {phrase}")

    curation = (ROOT / ".github/workflows/curation.yml").read_text(encoding="utf-8")
    for phrase in (
        "workflow_dispatch:",
        "confirmation:",
        "--confirm \"$CONFIRMATION\"",
        "CURATOR: ${{ github.actor }}",
        "scripts/curation/apply_action.py",
        "pull-requests: write",
        "## Changed files",
        "## Validation commands and results",
        "## Record counts after the change",
        "External retrieval performed",
        "Unresolved human decisions",
        "encoded_body",
        "&body=${encoded_body}",
        "Create the prefilled pull request",
    ):
        if phrase not in curation:
            fail(f"Curation workflow missing safeguard: {phrase}")


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
    for source in ("Consensus", "Scite", "Exa Search", "GitHub"):
        if source not in sources:
            fail(f"Source governance missing {source}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    if "living curated evidence map" not in readme:
        fail("README must preserve the living-archive limitation")
    expansion = (ROOT / "docs/methodology/expansion.md").read_text(
        encoding="utf-8"
    ).lower()
    for phrase in (
        "verificare la ricerca prima di fidarsi",
        "guardare indietro",
        "guardare avanti",
        "tre cicli completi consecutivi",
        "pannello di curatela",
    ):
        if phrase not in expansion:
            fail(f"Plain-language expansion guide missing safeguard: {phrase}")
    technical_expansion = (
        ROOT / "docs/methodology/expansion-reference.md"
    ).read_text(encoding="utf-8").lower()
    for phrase in (
        "known-item calibration",
        "source/query marginal yield",
        "backward and forward citation",
        "independent curator decision",
    ):
        if phrase not in technical_expansion:
            fail(f"Technical expansion reference missing safeguard: {phrase}")
    pages = (ROOT / "docs/operations/github-pages.md").read_text(
        encoding="utf-8"
    )
    for phrase in ("GitHub Actions", ".github/workflows/archive.yml", "site/"):
        if phrase not in pages:
            fail(f"GitHub Pages guide missing deployment element: {phrase}")

    metrics = (ROOT / "docs/operations/daily-metrics.md").read_text(
        encoding="utf-8"
    )
    metrics_flat = " ".join(metrics.split())
    for phrase in (
        "Nuovi candidati",
        "Tasso di nuovi candidati",
        "Completezza delle fonti",
        "non vengono trasformati in zero",
        "Consensus ed Exa",
        "relativi totali sono `null`",
        "non entra nella regola di arresto",
        "ledger GitHub #30",
    ):
        if phrase not in metrics_flat:
            fail(f"Daily metrics guide missing interpretation safeguard: {phrase}")

    automation = (ROOT / "docs/operations/automation.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "aggregate comment per batch",
        "successful zero-candidate run",
        "partial",
        "failed",
        "daily-metrics.md",
    ):
        if phrase not in automation:
            fail(f"Automation runbook missing daily-metrics contract: {phrase}")

    for schema_name in ("surveillance-run.schema.json", "research-stats.schema.json"):
        schema = json.loads((ROOT / "schema" / schema_name).read_text(encoding="utf-8"))
        if schema.get("additionalProperties") is not False:
            fail(f"{schema_name} must use a closed top-level schema")
    run_schema = json.loads(
        (ROOT / "schema/surveillance-run.schema.json").read_text(encoding="utf-8")
    )
    source_enum = run_schema["properties"]["expected_sources"]["items"].get("enum")
    if set(source_enum or []) != {"Consensus", "Exa"}:
        fail("Daily telemetry schema must enforce the governed active source set")
    metrics_builder = (ROOT / "scripts/metrics/surveillance.py").read_text(
        encoding="utf-8"
    )
    for phrase in (
        'ACTIVE_SOURCES = frozenset({"Consensus", "Exa"})',
        "summed(runs_subset",
    ):
        if phrase not in metrics_builder:
            fail(f"Daily metrics builder missing safeguard: {phrase}")

    with (ROOT / "data/registry/exclusion_reasons.csv").open(
        newline="", encoding="utf-8-sig"
    ) as handle:
        machine_codes = {
            row.get("code", "").strip() for row in csv.DictReader(handle)
        }
    codebook = (ROOT / "docs/methodology/eligibility.md").read_text(
        encoding="utf-8"
    )
    documented_codes = set(
        re.findall(r"^- `([A-Z][A-Z0-9_]+)`$", codebook, re.M)
    )
    if machine_codes != documented_codes:
        fail("Machine-readable exclusion reasons differ from the eligibility codebook")


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
