#!/usr/bin/env python3
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "WORKFLOW.md",
    ROOT / "docs/domain_allowlist_registry.md",
    ROOT / "docs/snowballing_execution_protocol.md",
    ROOT / "docs/NEXT_ACTION.md",
]

REGISTRY_HEADERS = {
    ROOT / "data/registry/papers.csv": {"paper_id", "title", "year"},
    ROOT / "data/registry/discovery_events.csv": {"event_id", "execution_id"},
    ROOT / "data/registry/screening_decisions.csv": {"decision_id", "paper_id", "decision"},
}


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def check_files():
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        fail(f"Missing required governance files: {', '.join(missing)}")


def check_registry_headers():
    for path, required in REGISTRY_HEADERS.items():
        if not path.exists():
            fail(f"Missing registry file: {path.relative_to(ROOT)}")
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])
        missing = sorted(required - headers)
        if missing:
            fail(f"{path.relative_to(ROOT)} missing required columns: {', '.join(missing)}")


def check_allowlist_minimum():
    path = ROOT / "docs/domain_allowlist_registry.md"
    txt = path.read_text(encoding="utf-8")
    required_domains = ["api.openalex.org", "api.crossref.org", "doi.org"]
    for d in required_domains:
        if d not in txt:
            fail(f"Domain allowlist missing expected domain: {d}")


def main():
    check_files()
    check_registry_headers()
    check_allowlist_minimum()
    print("[OK] Governance and registry baseline validation passed.")


if __name__ == "__main__":
    main()
