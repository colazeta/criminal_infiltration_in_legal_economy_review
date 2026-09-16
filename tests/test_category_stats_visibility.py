from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_categorisation_panel_is_moved_outside_hidden_bibliometric_content():
    source = (ROOT / "site" / "bibliometrics.js").read_text(encoding="utf-8")
    assert "import('./categorisation-statistics.js').then(() => {" in source
    assert "ui.content.after(categorisation)" in source


def test_empty_reviewed_corpus_does_not_hide_categorisation_panel_with_parent():
    source = (ROOT / "site" / "bibliometrics.js").read_text(encoding="utf-8")
    assert "ui.content.hidden = data.length === 0" in source
    assert "document.querySelector('#categorisation-statistics')" in source
