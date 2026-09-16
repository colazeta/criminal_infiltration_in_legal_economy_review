from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_statistics_page_busts_bibliometrics_cache_after_categorisation_release():
    html = (ROOT / "site" / "stats.html").read_text(encoding="utf-8")
    assert '<script src="./bibliometrics.js?v=002" defer></script>' in html


def test_15_september_malformed_terminals_have_exact_audited_recovery_chain():
    source = (ROOT / "scripts" / "metrics" / "fetch_surveillance_ledger_quarantine.py").read_text(encoding="utf-8")
    batch = 'ACADEMIC-2026-09-15-EXTRA-29aa300f6e53'
    assert f'5686212375: "{batch}"' in source
    assert f'5702142537: "{batch}"' in source
    assert '5702314461: {' in source
    assert f'"batch_id": "{batch}"' in source
    assert '"run_date": "2026-09-15"' in source
    assert '"created_rome_date": "2026-09-16"' in source
