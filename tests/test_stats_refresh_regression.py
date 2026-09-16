from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_statistics_page_busts_bibliometrics_cache_after_categorisation_release():
    html = (ROOT / "site" / "stats.html").read_text(encoding="utf-8")
    assert '<script src="./bibliometrics.js?v=002" defer></script>' in html


def test_15_september_malformed_terminal_has_exact_audited_recovery():
    source = (ROOT / "scripts" / "metrics" / "fetch_surveillance_ledger_quarantine.py").read_text(encoding="utf-8")
    assert '5686212375: "ACADEMIC-2026-09-15-EXTRA-29aa300f6e53"' in source
    assert '5702142537: {' in source
    assert '"batch_id": "ACADEMIC-2026-09-15-EXTRA-29aa300f6e53"' in source
    assert '"run_date": "2026-09-15"' in source
    assert '"created_rome_date": "2026-09-16"' in source
