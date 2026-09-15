#!/usr/bin/env python3
"""Current full-text calibration entry point.

The reviewed v4 API remains import-compatible for existing regression tests and
checkpoint tooling. Executable calibration is delegated lazily to the single
bounded v5 class-level remediation authorised by grouped trace audit #714.

The v5 module intentionally installs runtime hooks for its execution path. It is
therefore imported only inside ``main`` so importing this compatibility module
does not mutate the reviewed v4 contract used by checkpoint/regression tooling.
"""
from scripts.calibration.full_text_development_resume_v4 import *  # noqa: F401,F403
from scripts.calibration.full_text_development_resume_v4 import (  # noqa: F401
    _ORIGINAL_BUILD_PROPOSAL,
    _normalise_variable_analysis_relations,
)


def relation_normalising_build_proposal(target, source, atoms, synthesis):
    """Preserve the reviewed v4 patchable compatibility surface."""
    try:
        return _ORIGINAL_BUILD_PROPOSAL(target, source, atoms, synthesis)
    except ValueError as error:
        if str(error) != 'fulltext_variable_relation':
            raise

    repaired, changes = _normalise_variable_analysis_relations(synthesis)
    proposal = _ORIGINAL_BUILD_PROPOSAL(target, source, atoms, repaired)
    synthesis.clear()
    synthesis.update(repaired)
    RELATION_DIAGNOSTICS.update({
        'normalised_variable_relations': len(changes),
        'normalisation_digest': development.sha(development.canonical(changes)),
    })
    return proposal


def main():
    from scripts.calibration import full_text_development_resume_v5 as v5
    return v5.main()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
