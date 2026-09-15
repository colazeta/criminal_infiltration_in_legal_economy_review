#!/usr/bin/env python3
"""Run one authorised private calibration trace audit without publishing a proposal.

The runner reuses the existing exact-source/checkpoint machinery and intercepts the
synthesis graph immediately before proposal validation. Only a non-sensitive
structural count/digest file is written outside the encrypted scratch path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.calibration import full_text_development as development
from scripts.calibration import full_text_development_run as runtime
from scripts.calibration import full_text_development_resume as resume
from scripts.calibration.full_text_trace_audit import summarise_synthesis


def audit_path() -> Path:
    raw = os.environ.get("FULLTEXT_TRACE_AUDIT_FILE", "").strip()
    if not raw:
        raise RuntimeError("fulltext_trace_audit_file_unavailable")
    return Path(raw)


def auditing_build_proposal(target, source, atoms, synthesis):
    summary = summarise_synthesis(synthesis)
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Preserve the current fail-closed v4 proposal path. The audit records the
    # structure before any narrow normalisation is attempted.
    return resume.relation_normalising_build_proposal(target, source, atoms, synthesis)


def main() -> int:
    resume.reset_relation_diagnostics()
    prior_build = development.build_proposal
    prior_checkpoint_payload = runtime.runtime_checkpoint_payload
    development.build_proposal = auditing_build_proposal
    runtime.runtime_checkpoint_payload = resume.relation_checkpoint_payload
    try:
        return resume.v2.main()
    finally:
        development.build_proposal = prior_build
        runtime.runtime_checkpoint_payload = prior_checkpoint_payload


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        code = str(error)
        if code.startswith("fulltext_") or code.startswith("OA "):
            raise SystemExit(code) from None
        raise SystemExit("fulltext_trace_audit_failed") from None
