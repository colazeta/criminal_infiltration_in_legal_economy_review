#!/usr/bin/env python3
"""Validate the repository's governance, schemas and publication boundary."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "WORKFLOW.md",
    ROOT / "README.md",
    ROOT / "docs/domain_allowlist_registry.md",
    ROOT / "docs/snowballing_execution_protocol.md",
    ROOT / "docs/literature_review_protocol.md",
    ROOT / "docs/eligibility_codebook.md",
    ROOT / "docs/archive_data_model.md",
    ROOT / "docs/saturation_metrics.md",
    ROOT / "docs/NEXT_ACTION.md",
    ROOT / "scripts/build_archive.py",
    ROOT / "scripts/validation/validate_archive.py",
    ROOT / "scripts/validation/validate_site.py",
    ROOT / "site/index.html",
    ROOT / "site/app.js",
    ROOT / "site/styles.css",
    ROOT / ".github/workflows/deploy-pages.yml",
]

REGISTRY_HEADERS = {
    ROOT / "data/registry/papers.csv": {
        "paper_id",
        "doi",
        "title",
        "authors",
        "year",
        "venue",
        "canonical_status",
    },
    ROOT / "data/registry/discovery_events.csv": {
        "event_id",
        "paper_id",
        "execution_id",
        "feed_type",
        "source_name",
    },
    ROOT / "data/registry/screening_decisions.csv": {
        "decision_id",
        "paper_id",
        "screening_stage",
        "decision",
        "confidence",
        "decision_date",
        "is_current",
    },
    ROOT / "data/registry/paper_codes.csv": {"paper_id", "dimension", "code"},
    ROOT / "data/registry/execution_metrics.csv": {"execution_id", "execution_date"},
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def check_files() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        fail(f"Missing required files: {', '.join(missing)}")


def check_registry_headers() -> None:
    for path, required in REGISTRY_HEADERS.items():
        if not path.exists():
            fail(f"Missing registry file: {path.relative_to(ROOT)}")
        with path.open(newline="", encoding="utf-8-sig") as handle:
            headers = set(csv.DictReader(handle).fieldnames or [])
        missing = sorted(required - headers)
        if missing:
            fail(f"{path.relative_to(ROOT)} missing columns: {', '.join(missing)}")


def check_allowlist() -> None:
    text = (ROOT / "docs/domain_allowlist_registry.md").read_text(encoding="utf-8")
    for domain in ("api.openalex.org", "api.crossref.org", "doi.org"):
        if domain not in text:
            fail(f"Domain allowlist missing expected domain: {domain}")


def check_issue_forms() -> None:
    for path in sorted((ROOT / ".github/ISSUE_TEMPLATE").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "\nabout:" in f"\n{text}":
            fail(f"{path.relative_to(ROOT)} uses invalid 'about' instead of 'description'")
        for key in ("name:", "description:", "body:"):
            if not any(line.startswith(key) for line in text.splitlines()):
                fail(f"{path.relative_to(ROOT)} missing top-level {key[:-1]}")


def check_no_placeholders() -> None:
    for path in sorted((ROOT / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "Placeholder script for project pipeline step" in text:
            fail(f"Unimplemented pipeline placeholder: {path.relative_to(ROOT)}")


def check_public_boundary() -> None:
    builder = (ROOT / "scripts/build_archive.py").read_text(encoding="utf-8")
    if "data/registry/papers.csv" not in builder:
        fail("Public archive builder does not declare the canonical papers registry")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "living curated evidence map" not in readme.lower():
        fail("README must state that the archive is living and curated")


def main() -> None:
    check_files()
    check_registry_headers()
    check_allowlist()
    check_issue_forms()
    check_no_placeholders()
    check_public_boundary()
    print("[OK] Governance, schema and publication-boundary validation passed.")


if __name__ == "__main__":
    try:
        main()
    except (csv.Error, OSError) as exc:
        fail(str(exc))
