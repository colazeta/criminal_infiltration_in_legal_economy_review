#!/usr/bin/env python3
"""Runtime policy for the bounded full-text calibration development harness.

Operational model timeouts are deliberately outside the scientific extractor
fingerprint. They may be enlarged after a technical timeout without changing
prompts, decoding, source coverage, evidence validation or proposal semantics.
"""
from scripts.calibration import full_text_development as development

CHUNK_TIMEOUT_SECONDS = 600
SYNTHESIS_TIMEOUT_SECONDS = 720


def runtime_timeout(requested):
    if not isinstance(requested, (int, float)) or requested <= 0:
        raise ValueError('fulltext_runtime_timeout_invalid')
    if requested <= 300:
        return max(requested, CHUNK_TIMEOUT_SECONDS)
    return max(requested, SYNTHESIS_TIMEOUT_SECONDS)


def runtime_post(original, payload, timeout=300):
    try:
        return original(payload, timeout=runtime_timeout(timeout))
    except TimeoutError:
        raise RuntimeError('fulltext_model_timeout') from None


def main():
    original = development.post_model
    development.post_model = lambda payload, timeout=300: runtime_post(original, payload, timeout)
    try:
        development.main()
    finally:
        development.post_model = original


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error)
        if code.startswith('fulltext_') or code.startswith('OA '):
            raise SystemExit(code) from None
        raise SystemExit('fulltext_calibration_development_failed') from None
