#!/usr/bin/env python3
"""Check that a checkout has the directories and files needed for archive work."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    ROOT / "AGENTS.md",
    ROOT / "docs/literature_review_protocol.md",
    ROOT / "docs/eligibility_codebook.md",
    ROOT / "docs/archive_data_model.md",
    ROOT / "data/registry/papers.csv",
    ROOT / "data/registry/discovery_events.csv",
    ROOT / "data/registry/screening_decisions.csv",
    ROOT / "site/index.html",
]


def main() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_PATHS if not path.exists()]
    if missing:
        print(f"[FAIL] Missing required paths: {', '.join(missing)}")
        raise SystemExit(1)

    commands = [
        [sys.executable, "scripts/validation/validate_repo_governance.py"],
        [sys.executable, "scripts/build_archive.py"],
        [sys.executable, "scripts/validation/validate_archive.py"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    print("[OK] Project checkout is ready for governed archive work.")


if __name__ == "__main__":
    main()
