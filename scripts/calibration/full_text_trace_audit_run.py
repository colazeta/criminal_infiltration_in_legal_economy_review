#!/usr/bin/env python3
"""Run one authorised private calibration trace audit without publishing a proposal.

The runner reuses the existing exact-source/checkpoint machinery and intercepts the
synthesis graph immediately before proposal validation. Only a non-sensitive
structural count/digest file is written outside the encrypted scratch path.

Audit mode is checkpoint-reuse only: if any expected chunk checkpoint is absent,
the run fails closed instead of performing new chunk inference. The only model
call permitted by this audit is the synthesis call over already retained exact
chunk outputs.
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
    prior_pass_limit = resume.v2.pass_limit
    prior_requires_complete = resume.v2.pass_requires_complete
    development.build_proposal = auditing_build_proposal
    runtime.runtime_checkpoint_payload = resume.relation_checkpoint_payload
    # Zero is deliberately injected here rather than accepted by the production
    # environment parser. In v2 resumable_post, a missing checkpoint therefore
    # raises pass_budget_exhausted before any new chunk model call can occur.
    resume.v2.pass_limit = lambda: 0
    resume.v2.pass_requires_complete = lambda: True
    try:
        return resume.v2.main()
    finally:
        development.build_proposal = prior_build
        runtime.runtime_checkpoint_payload = prior_checkpoint_payload
        resume.v2.pass_limit = prior_pass_limit
        resume.v2.pass_requires_complete = prior_requires_complete


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        code = str(error)
        if code.startswith("fulltext_") or code.startswith("OA "):
            raise SystemExit(code) from None
        raise SystemExit("fulltext_trace_audit_failed") from None
