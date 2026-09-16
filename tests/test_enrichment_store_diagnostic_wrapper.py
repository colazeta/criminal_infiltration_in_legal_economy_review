from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_diagnostic_wrapper_is_fail_closed_and_redacted():
    source = (ROOT / "curator-app/src/worker-diagnostic.js").read_text(encoding="utf-8")
    assert "store_internal_exception" in source
    assert "service_operation_failed" in source
    assert "console.error" in source
    assert "error.stack" not in source
    assert "JSON.stringify(error)" not in source
    assert "request.text" not in source
    assert "request.json" not in source


def test_worker_configuration_uses_diagnostic_wrapper_without_changing_do_identity():
    config = (ROOT / "curator-app/wrangler.example.jsonc").read_text(encoding="utf-8")
    assert '"main": "src/worker-diagnostic.js"' in config
    assert '"name": "ENRICHMENT_STORE"' in config
    assert '"class_name": "PaperEnrichmentStore"' in config
    assert '"tag": "v2-private-enrichment"' in config
